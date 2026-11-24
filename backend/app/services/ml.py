"""Pelatihan model dan prediksi IP semester berikutnya.

Aturan penting:
- Fitur hanya berasal dari semester SEBELUM semester sasaran (tanpa data leakage).
- Pembagian data berdasarkan waktu bila ada >= 2 semester sasaran. Jika hanya ada 1
  (data uji coba), dipakai pembagian acak dan ditandai sebagai EKSPERIMEN.
- Model baru layak dipakai jika MAE-nya lebih kecil dari baseline (IP terakhir dianggap sama).
"""
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..config import MODEL_DIR
from ..db import get_db
from ..utils import chunks, fetch_all, one

FEATURES = ["ip_last", "ipk_last", "ip_prev", "ip_delta", "ip_mean", "ip_std",
            "n_fail_last", "credits_last", "n_sem"]
FAIL_LETTERS = {"D", "E"}
MIN_PAIRS = 40


def load():
    recs = fetch_all("academic_records",
                     "student_id,semester_id,semester_gpa,cumulative_gpa,credits_taken,cumulative_credits")
    sems = {s["id"]: s for s in fetch_all("semesters", "id,code,sort_order")}
    fails = {}
    for e in fetch_all("enrollments", "student_id,semester_id,course_grades(letter)"):
        cg = one(e.get("course_grades"))
        if cg and cg.get("letter") in FAIL_LETTERS:
            k = (e["student_id"], e["semester_id"])
            fails[k] = fails.get(k, 0) + 1
    return recs, sems, fails


def feats(hist, fails):
    """hist = catatan akademik satu mahasiswa sampai semester t (urut naik)."""
    g = [float(r["semester_gpa"]) for r in hist]
    last = hist[-1]
    prev = g[-2] if len(g) > 1 else g[-1]
    return {
        "ip_last": g[-1],
        "ipk_last": float(last["cumulative_gpa"] if last["cumulative_gpa"] is not None else g[-1]),
        "ip_prev": prev,
        "ip_delta": g[-1] - prev,
        "ip_mean": float(np.mean(g)),
        "ip_std": float(np.std(g)) if len(g) > 1 else 0.0,
        "n_fail_last": fails.get((last["student_id"], last["semester_id"]), 0),
        "credits_last": float(last["credits_taken"] or 0),
        "n_sem": len(g),
    }


def _by_student(recs, sems):
    order = {i: s["sort_order"] for i, s in sems.items()}
    by = {}
    for r in recs:
        if r["semester_gpa"] is not None and r["semester_id"] in order:
            by.setdefault(r["student_id"], []).append(r)
    for lst in by.values():
        lst.sort(key=lambda r: order[r["semester_id"]])
    return by, order


def build_dataset(recs, sems, fails) -> pd.DataFrame:
    by, order = _by_student(recs, sems)
    rows = []
    for lst in by.values():
        for i in range(len(lst) - 1):
            f = feats(lst[:i + 1], fails)
            f["target"] = float(lst[i + 1]["semester_gpa"])
            f["t_order"] = order[lst[i + 1]["semester_id"]]
            rows.append(f)
    return pd.DataFrame(rows)


def _metrics(y, p):
    p = np.clip(p, 0, 4)
    return {"mae": float(mean_absolute_error(y, p)),
            "rmse": float(np.sqrt(mean_squared_error(y, p))),
            "r2": float(r2_score(y, p))}


def fit_and_evaluate(df: pd.DataFrame):
    if len(df) < MIN_PAIRS:
        raise ValueError(f"Data belum cukup: butuh minimal {MIN_PAIRS} pasang (mahasiswa, semester), "
                         f"baru ada {len(df)}.")
    orders = sorted(df["t_order"].unique())
    if len(orders) >= 2:
        k = max(1, int(round(len(orders) * 0.2)))
        test_orders = orders[-k:]
        tr, te = df[~df["t_order"].isin(test_orders)], df[df["t_order"].isin(test_orders)]
        note = f"pembagian berbasis waktu, sasaran urutan semester {orders[0]}-{orders[-1]}, uji: {test_orders}"
    else:
        te = df.sample(frac=0.2, random_state=42)
        tr = df.drop(te.index)
        note = "EKSPERIMEN: hanya 1 semester sasaran, pembagian acak 80/20 (bukan berbasis waktu)"
    if len(tr) < 30 or len(te) < 5:
        raise ValueError("Pembagian latih/uji terlalu kecil. Tambahkan data riwayat.")
    candidates = {
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Ridge Regression": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "Random Forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, learning_rate=0.05,
                                                       max_depth=2, random_state=42),
    }
    results = {}
    for name, m in candidates.items():
        m.fit(tr[FEATURES], tr["target"])
        results[name] = _metrics(te["target"], m.predict(te[FEATURES]))
    baseline = _metrics(te["target"], te["ip_last"].to_numpy())
    best = min(results, key=lambda n: results[n]["mae"])
    final = candidates[best]
    final.fit(df[FEATURES], df["target"])  # latih ulang dengan semua data
    return {"best": best, "model": final, "results": results, "baseline": baseline,
            "n_train": int(len(tr)), "n_test": int(len(te)), "note": note}


def train(created_by: str):
    recs, sems, fails = load()
    out = fit_and_evaluate(build_dataset(recs, sems, fails))
    db = get_db()
    n = len(db.table("model_versions").select("id").execute().data) + 1
    version = f"v{n}"
    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, f"{version}.joblib")
    joblib.dump({"model": out["model"], "features": FEATURES}, path)
    m = out["results"][out["best"]]
    row = db.table("model_versions").insert({
        "version": version, "algorithm": out["best"], "training_semesters": out["note"],
        "mae": round(m["mae"], 3), "rmse": round(m["rmse"], 3), "r2": round(m["r2"], 3),
        "baseline_mae": round(out["baseline"]["mae"], 3), "artifact_path": path,
        "is_active": False, "created_by": created_by,
    }).execute().data[0]
    return {"model": row, "candidates": out["results"], "baseline": out["baseline"],
            "better_than_baseline": m["mae"] < out["baseline"]["mae"],
            "n_train": out["n_train"], "n_test": out["n_test"]}


def categorize(delta: float, thr: float) -> str:
    if delta <= -thr:
        return "berpotensi_menurun"
    if delta >= thr:
        return "berpotensi_meningkat"
    return "stabil"


def predict_all(target_semester_id: int, thr: float | None = None):
    db = get_db()
    mv = db.table("model_versions").select("*").eq("is_active", True).execute().data
    if not mv:
        raise ValueError("Belum ada model aktif. Latih dan aktifkan model dulu.")
    mv = mv[0]
    model = joblib.load(mv["artifact_path"])["model"]
    recs, sems, fails = load()
    if target_semester_id not in sems:
        raise ValueError("Semester sasaran tidak ditemukan.")
    by, order = _by_student(recs, sems)
    t_order = order[target_semester_id]
    # Batas kategori: perubahan lebih kecil dari kesalahan rata-rata model bukan sinyal.
    # Sebaiknya divalidasi dengan data kampus.
    thr = thr if thr is not None else max(0.05, float(mv["mae"] or 0.1))

    credits = {c["id"]: c["credits"] for c in fetch_all("courses", "id,credits")}
    new_credits = {}
    for e in fetch_all("enrollments", "student_id,course_id", semester_id=target_semester_id):
        new_credits[e["student_id"]] = new_credits.get(e["student_id"], 0) + credits.get(e["course_id"], 0)
    actual = {r["student_id"]: r["semester_gpa"] for r in recs
              if r["semester_id"] == target_semester_id and r["semester_gpa"] is not None}

    meta, X = [], []
    for sid, lst in by.items():
        hist = [r for r in lst if order[r["semester_id"]] < t_order]
        if not hist:
            continue
        f = feats(hist, fails)
        X.append([f[c] for c in FEATURES])
        meta.append((sid, f["ip_last"], hist[-1]))
    if not X:
        raise ValueError("Tidak ada mahasiswa dengan riwayat sebelum semester sasaran.")
    preds = np.clip(model.predict(pd.DataFrame(X, columns=FEATURES)), 0, 4)

    payload = []
    for (sid, ip_last, last), p in zip(meta, preds):
        ip = round(float(p), 2)
        cum = float(last["cumulative_gpa"] if last["cumulative_gpa"] is not None else ip_last)
        cum_cr = int(last["cumulative_credits"] or 0)
        add_cr = int(new_credits.get(sid) or last["credits_taken"] or 0)
        ipk = (cum * cum_cr + ip * add_cr) / (cum_cr + add_cr) if cum_cr + add_cr > 0 else ip
        payload.append({
            "student_id": sid, "target_semester_id": target_semester_id,
            "model_version_id": mv["id"], "predicted_ip": ip,
            "predicted_ipk": round(min(ipk, 4.0), 2),
            "category": categorize(ip - ip_last, thr),
            "actual_ip": float(actual[sid]) if sid in actual else None,
        })
    for part in chunks(payload):
        db.table("predictions").upsert(
            part, on_conflict="student_id,target_semester_id,model_version_id").execute()
    return {"count": len(payload), "model": mv["version"], "threshold": round(thr, 3)}