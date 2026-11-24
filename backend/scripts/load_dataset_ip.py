"""Memuat dataset_prediksi_ip_semester_berikutnya.csv ke Supabase (tanpa pandas/NumPy).

Kolom CSV: student_id, semester, ip, sks, ipk, target_ip_semester_berikutnya

Pemakaian (dari folder backend, venv aktif):
    python scripts/load_dataset_ip.py data/dataset_prediksi_ip_semester_berikutnya.csv

Catatan:
- Kolom target_ip_semester_berikutnya TIDAK dimuat. Sistem membentuk target sendiri dari IP
  semester berikutnya (hasilnya sama persis), jadi tidak ada duplikasi dan tidak ada kebocoran data.
- Dibuat satu semester kosong tambahan (semester terakhir + 1) sebagai semester sasaran prediksi.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

REQUIRED = ["student_id", "semester", "ip", "sks", "ipk"]
PROGRAM = {"code": "UMUM", "name": "Program Studi Contoh"}
ENTRY_YEAR = 2023  # nilai sementara, dataset tidak memuat angkatan


def clamp4(x: float) -> float:
    return round(min(max(x, 0.0), 4.0), 2)


def read_rows(path: str):
    """Baca CSV, validasi, urutkan, dan hitung total SKS kumulatif per mahasiswa."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        first = f.readline()
        f.seek(0)
        delim = ";" if first.count(";") > first.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)
        cols = [(c or "").strip().lower() for c in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED if c not in cols]
        if missing:
            sys.exit(f"Kolom tidak ditemukan di CSV: {missing}")
        rows, skipped = [], 0
        for r in reader:
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            try:
                rows.append({
                    "student_id": r["student_id"],
                    "semester": int(float(r["semester"])),
                    "ip": clamp4(float(r["ip"])),
                    "sks": int(float(r["sks"])),
                    "ipk": clamp4(float(r["ipk"])),
                })
            except (ValueError, KeyError):
                skipped += 1
    rows = [r for r in rows if r["student_id"]]
    rows.sort(key=lambda r: (r["student_id"], r["semester"]))
    seen, cum = set(), {}
    for r in rows:
        key = (r["student_id"], r["semester"])
        if key in seen:
            sys.exit(f"Baris ganda untuk {key}. Perbaiki CSV dulu.")
        seen.add(key)
        cum[r["student_id"]] = cum.get(r["student_id"], 0) + r["sks"]
        r["cum_sks"] = cum[r["student_id"]]
    return rows, skipped


def main(path: str):
    from app.db import get_db
    from app.utils import chunks, fetch_all

    rows, skipped = read_rows(path)
    ids = sorted({r["student_id"] for r in rows})
    max_sem = max(r["semester"] for r in rows)
    print(f"Baris valid: {len(rows)} | mahasiswa: {len(ids)} | semester: 1-{max_sem}"
          + (f" | dilewati: {skipped}" if skipped else ""), flush=True)
    db = get_db()

    # 1. Program studi (satu program contoh)
    db.table("academic_programs").upsert([PROGRAM], on_conflict="code").execute()
    prog = {p["code"]: p["id"] for p in fetch_all("academic_programs", "id,code")}[PROGRAM["code"]]

    # 2. Semester S1..S(n) + satu semester kosong sebagai sasaran prediksi
    db.table("semesters").upsert([
        {"code": f"S{n}", "academic_year": "Data contoh", "term": 1 if n % 2 else 2,
         "sort_order": n, "is_active": False} for n in range(1, max_sem + 2)
    ], on_conflict="code").execute()
    sem = {s["code"]: s["id"] for s in fetch_all("semesters", "id,code")}
    print(f"Semester dibuat: S1-S{max_sem + 1} (S{max_sem + 1} kosong, untuk prediksi)", flush=True)

    # 3. Mahasiswa (tanpa data pribadi)
    students = [{"student_number": s, "full_name": f"Mahasiswa {s}", "program_id": prog,
                 "entry_year": ENTRY_YEAR} for s in ids]
    for part in chunks(students):
        db.table("students").upsert(part, on_conflict="student_number").execute()
    sid = {s["student_number"]: s["id"] for s in fetch_all("students", "id,student_number")}
    print(f"Mahasiswa: {len(students)}", flush=True)

    # 4. Catatan akademik: IP, SKS, IPK dari CSV
    recs = [{"student_id": sid[r["student_id"]], "semester_id": sem[f"S{r['semester']}"],
             "semester_gpa": r["ip"], "cumulative_gpa": r["ipk"],
             "credits_taken": r["sks"], "cumulative_credits": r["cum_sks"]} for r in rows]
    done = 0
    for part in chunks(recs):
        db.table("academic_records").upsert(part, on_conflict="student_id,semester_id").execute()
        done += len(part)
        print(f"Catatan akademik: {done}/{len(recs)}", flush=True)
    print(f"Selesai: {len(students)} mahasiswa, {len(recs)} catatan akademik.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Pemakaian: python scripts/load_dataset_ip.py data/dataset_prediksi_ip_semester_berikutnya.csv")
    main(sys.argv[1])