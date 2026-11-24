from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from ..deps import User, current_user, require
from ..scope import assert_student_access, visible_student_ids
from ..utils import fetch_all, one

router = APIRouter(tags=["views"])
staff = require("admin", "dosen")


def db():
    return get_db()


def sems():
    return db().table("semesters").select("id,code,sort_order").order("sort_order").execute().data


def default_target():
    """Semester sasaran terbaru yang sudah punya prediksi."""
    for s in sorted(sems(), key=lambda s: -s["sort_order"]):
        if db().table("predictions").select("id").eq("target_semester_id", s["id"]).limit(1).execute().data:
            return s
    return None


def last_records_before(t_order: int, ids=None):
    order = {s["id"]: s["sort_order"] for s in sems()}
    best = {}
    for r in fetch_all("academic_records", "student_id,semester_id,semester_gpa,cumulative_gpa"):
        o = order.get(r["semester_id"])
        if o is None or o >= t_order or (ids is not None and r["student_id"] not in ids):
            continue
        cur = best.get(r["student_id"])
        if cur is None or o > cur[0]:
            best[r["student_id"]] = (o, r)
    return {k: v[1] for k, v in best.items()}


def target_predictions(tid: int, ids):
    """Prediksi untuk semester sasaran dari model yang sedang aktif."""
    mv = db().table("model_versions").select("id").eq("is_active", True).execute().data
    q = {"target_semester_id": tid}
    if mv:
        q["model_version_id"] = mv[0]["id"]
    rows = fetch_all("predictions", "*,students(student_number,full_name)", **q)
    return [r for r in rows if ids is None or r["student_id"] in ids]


def f(x):
    return float(x) if x is not None else None


def pred_row(p, lr):
    st = one(p.get("students")) or {}
    last = lr.get(p["student_id"])
    return {"id": p["id"], "student_id": p["student_id"], "student_number": st.get("student_number"),
            "name": st.get("full_name"), "last_ip": f(last["semester_gpa"]) if last else None,
            "predicted_ip": f(p["predicted_ip"]), "predicted_ipk": f(p["predicted_ipk"]),
            "category": p["category"], "actual_ip": f(p["actual_ip"]), "followed_up": p["followed_up"]}


def pick_target(semester_id):
    S = sems()
    if semester_id:
        t = next((s for s in S if s["id"] == semester_id), None)
        if not t:
            raise HTTPException(404, "Semester tidak ditemukan")
        return t
    return default_target()


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user.model_dump()


@router.get("/meta")
def meta(user: User = Depends(current_user)):
    return {"letters": [g["letter"] for g in fetch_all("grade_scale", "letter,points")],
            "semesters": sems()}


@router.get("/dashboard")
def dashboard(user: User = Depends(staff)):
    ids = visible_student_ids(user)
    S = sems()
    order = {s["id"]: s["sort_order"] for s in S}
    code = {s["id"]: s["code"] for s in S}
    total = len(ids) if ids is not None else len(fetch_all("students", "id"))
    recs = [r for r in fetch_all("academic_records", "student_id,semester_id,semester_gpa")
            if ids is None or r["student_id"] in ids]
    agg = {}
    for r in recs:
        if r["semester_gpa"] is not None:
            agg.setdefault(r["semester_id"], []).append(float(r["semester_gpa"]))
    trend = [{"semester": code[sid], "ip": round(sum(v) / len(v), 2)}
             for sid, v in sorted(agg.items(), key=lambda kv: order[kv[0]])]
    latest = last_records_before(10 ** 9, ids)
    ipks = [float(r["cumulative_gpa"]) for r in latest.values() if r["cumulative_gpa"] is not None]
    out = {"target": None, "total_students": total,
           "avg_ipk": round(sum(ipks) / len(ipks), 2) if ipks else None,
           "avg_pred_ip": None, "need_attention": 0,
           "categories": {"stabil": 0, "berpotensi_meningkat": 0, "berpotensi_menurun": 0},
           "trend": trend, "watchlist": []}
    tgt = default_target()
    if tgt:
        preds = target_predictions(tgt["id"], ids)
        lr = last_records_before(tgt["sort_order"], ids)
        rows = [pred_row(p, lr) for p in preds]
        out["target"] = tgt["code"]
        if rows:
            out["avg_pred_ip"] = round(sum(r["predicted_ip"] for r in rows) / len(rows), 2)
        for r in rows:
            out["categories"][r["category"]] += 1
        down = [r for r in rows if r["category"] == "berpotensi_menurun"]
        out["need_attention"] = sum(1 for r in down if not r["followed_up"])
        down.sort(key=lambda r: (r["predicted_ip"] - (r["last_ip"] or r["predicted_ip"])))
        out["watchlist"] = down[:5]
    return out


@router.get("/predictions")
def predictions(semester_id: int | None = None, user: User = Depends(staff)):
    ids = visible_student_ids(user)
    tgt = pick_target(semester_id)
    if not tgt:
        return {"target": None, "rows": []}
    lr = last_records_before(tgt["sort_order"], ids)
    rows = [pred_row(p, lr) for p in target_predictions(tgt["id"], ids)]
    rows.sort(key=lambda r: (r["name"] or ""))
    return {"target": tgt["code"], "rows": rows}


@router.get("/predictions/student/{sid}")
def student_detail(sid: int, user: User = Depends(staff)):
    assert_student_access(user, sid)
    st = one(db().table("students").select("*,academic_programs(code,name)").eq("id", sid).execute().data)
    if not st:
        raise HTTPException(404, "Mahasiswa tidak ditemukan")
    S = {s["id"]: s for s in sems()}
    recs = sorted(fetch_all("academic_records", "*", student_id=sid), key=lambda r: S[r["semester_id"]]["sort_order"])
    active = {m["id"] for m in db().table("model_versions").select("id").eq("is_active", True).execute().data}
    preds = [p for p in fetch_all("predictions", "*", student_id=sid) if not active or p["model_version_id"] in active]
    preds.sort(key=lambda p: S[p["target_semester_id"]]["sort_order"])
    return {"student": st,
            "records": [{"semester": S[r["semester_id"]]["code"], "ip": f(r["semester_gpa"]),
                         "ipk": f(r["cumulative_gpa"]), "sks": r["credits_taken"]} for r in recs],
            "predictions": [{"id": p["id"], "target": S[p["target_semester_id"]]["code"],
                             "predicted_ip": f(p["predicted_ip"]), "predicted_ipk": f(p["predicted_ipk"]),
                             "category": p["category"], "actual_ip": f(p["actual_ip"]),
                             "followed_up": p["followed_up"]} for p in preds]}


@router.get("/alerts")
def alerts(user: User = Depends(staff)):
    ids = visible_student_ids(user)
    tgt = default_target()
    if not tgt:
        return {"target": None, "rows": []}
    lr = last_records_before(tgt["sort_order"], ids)
    rows = [pred_row(p, lr) for p in target_predictions(tgt["id"], ids) if p["category"] == "berpotensi_menurun"]
    rows.sort(key=lambda r: (r["followed_up"], (r["predicted_ip"] - (r["last_ip"] or r["predicted_ip"]))))
    return {"target": tgt["code"], "rows": rows}


@router.post("/alerts/{pid}/follow-up")
def follow_up(pid: int, user: User = Depends(staff)):
    p = one(db().table("predictions").select("id,student_id").eq("id", pid).execute().data)
    if not p:
        raise HTTPException(404, "Prediksi tidak ditemukan")
    assert_student_access(user, p["student_id"])
    db().table("predictions").update({"followed_up": True, "followed_up_by": user.id,
                                      "followed_up_at": datetime.now(timezone.utc).isoformat()}).eq("id", pid).execute()
    return {"ok": True}


@router.get("/history")
def history(user: User = Depends(staff)):
    ids = visible_student_ids(user)
    S = {s["id"]: s["code"] for s in sems()}
    rows = fetch_all("predictions", "*,students(student_number,full_name),model_versions(version)")
    rows = [r for r in rows if ids is None or r["student_id"] in ids]
    rows.sort(key=lambda r: -r["id"])
    out = [{"id": r["id"], "student_number": (one(r["students"]) or {}).get("student_number"),
            "name": (one(r["students"]) or {}).get("full_name"), "target": S.get(r["target_semester_id"]),
            "version": (one(r["model_versions"]) or {}).get("version"),
            "predicted_ip": f(r["predicted_ip"]), "actual_ip": f(r["actual_ip"]),
            "abs_error": f(r["abs_error"])} for r in rows[:500]]
    errs = [r["abs_error"] for r in out if r["abs_error"] is not None]
    return {"rows": out, "with_actual": len(errs),
            "mean_abs_error": round(sum(errs) / len(errs), 3) if errs else None}


@router.get("/student/me")
def student_me(user: User = Depends(require("mahasiswa"))):
    st = one(db().table("students").select("*").eq("profile_id", user.id).execute().data)
    if not st:
        raise HTTPException(404, "Akun Anda belum dihubungkan ke data mahasiswa. Hubungi Admin.")
    S = {s["id"]: s for s in sems()}
    recs = sorted(fetch_all("academic_records", "*", student_id=st["id"]),
                  key=lambda r: S[r["semester_id"]]["sort_order"])
    grades = []
    if recs:
        enr = fetch_all("enrollments", "id,courses(code,name,credits),course_grades(letter,status)",
                        student_id=st["id"], semester_id=recs[-1]["semester_id"])
        for e in enr:
            cg = one(e.get("course_grades")) or {}
            if cg.get("status") == "final":
                grades.append({**e["courses"], "letter": cg["letter"]})
    prediction = None
    tgt = default_target()
    if tgt:
        rows = target_predictions(tgt["id"], {st["id"]})
        if rows:
            prediction = {"target": tgt["code"], "predicted_ip": f(rows[0]["predicted_ip"]),
                          "predicted_ipk": f(rows[0]["predicted_ipk"])}
    return {"student": {"name": st["full_name"], "student_number": st["student_number"]},
            "records": [{"semester": S[r["semester_id"]]["code"], "ip": f(r["semester_gpa"]),
                         "ipk": f(r["cumulative_gpa"]), "sks": r["credits_taken"],
                         "total_sks": r["cumulative_credits"]} for r in recs],
            "grades": grades, "prediction": prediction}