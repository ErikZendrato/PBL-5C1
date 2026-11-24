"""Memuat dataset Kaggle (contoh) ke Supabase untuk uji coba end-to-end.

Pemakaian (dari folder backend, venv aktif):
    python scripts/load_kaggle.py data/students.csv          # semua baris
    python scripts/load_kaggle.py data/students.csv 3000     # contoh acak 3000 baris

Hanya kolom akademik yang dipakai. Kolom demografi sengaja diabaikan.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pandas as pd  # noqa: E402

from app.db import get_db  # noqa: E402
from app.utils import chunks, fetch_all  # noqa: E402

CODES = {"STEM": "STEM", "Arts & Humanities": "ARTS", "Business": "BUS",
         "Health Sciences": "HLT", "Law & Social Sciences": "LAW"}


def prog_code(name: str) -> str:
    return CODES.get(name) or re.sub(r"[^A-Z0-9]", "", name.upper())[:8] or "UMUM"


def number(pid) -> str:
    return f"K{int(pid):05d}"


def main(path: str, limit: int | None):
    df = pd.read_csv(path, sep=None, engine="python")  # deteksi otomatis koma atau tab
    need = ["person_id", "course_type", "units_enrolled", "gpa_semester_1", "gpa_semester_2"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        sys.exit(f"Kolom tidak ditemukan di CSV: {missing}")
    df = df.dropna(subset=need)
    df = df.assign(
        gpa_semester_1=df["gpa_semester_1"].clip(0, 4).round(2),
        gpa_semester_2=df["gpa_semester_2"].clip(0, 4).round(2),
        units=df["units_enrolled"].astype(int).clip(lower=1),
    )
    print(f"Baris valid di CSV: {len(df)}")
    if limit and limit < len(df):
        df = df.sample(n=limit, random_state=42)
        print(f"Memakai contoh acak: {len(df)} baris")

    db = get_db()

    # 1. Program studi (dari course_type)
    types = sorted(df["course_type"].unique())
    db.table("academic_programs").upsert(
        [{"code": prog_code(t), "name": t} for t in types], on_conflict="code").execute()
    prog = {p["code"]: p["id"] for p in fetch_all("academic_programs", "id,code")}
    print(f"Program studi: {len(types)}")

    # 2. Semester: S1 dan S2
    db.table("semesters").upsert([
        {"code": "S1", "academic_year": "Data contoh", "term": 1, "sort_order": 1, "is_active": False},
        {"code": "S2", "academic_year": "Data contoh", "term": 2, "sort_order": 2, "is_active": False},
    ], on_conflict="code").execute()
    sem = {s["code"]: s["id"] for s in fetch_all("semesters", "id,code")}

    # 3. Mahasiswa (tanpa data pribadi: ID dan nama dibuat otomatis)
    students = [{"student_number": number(r.person_id), "full_name": f"Mahasiswa {int(r.person_id)}",
                 "program_id": prog[prog_code(r.course_type)], "entry_year": 2024}
                for r in df.itertuples()]
    done = 0
    for part in chunks(students):
        db.table("students").upsert(part, on_conflict="student_number").execute()
        done += len(part)
        print(f"Mahasiswa: {done}/{len(students)}", flush=True)
    sid = {s["student_number"]: s["id"] for s in fetch_all("students", "id,student_number")}

    # 4. Catatan akademik: IP semester 1 dan 2, IPK dihitung dari keduanya
    recs = []
    for r in df.itertuples():
        s, u = sid[number(r.person_id)], int(r.units)
        g1, g2 = float(r.gpa_semester_1), float(r.gpa_semester_2)
        recs.append({"student_id": s, "semester_id": sem["S1"], "semester_gpa": g1,
                     "cumulative_gpa": g1, "credits_taken": u, "cumulative_credits": u})
        recs.append({"student_id": s, "semester_id": sem["S2"], "semester_gpa": g2,
                     "cumulative_gpa": round((g1 + g2) / 2, 2), "credits_taken": u,
                     "cumulative_credits": 2 * u})
    done = 0
    for part in chunks(recs):
        db.table("academic_records").upsert(part, on_conflict="student_id,semester_id").execute()
        done += len(part)
        print(f"Catatan akademik: {done}/{len(recs)}", flush=True)

    print(f"Selesai: {len(students)} mahasiswa, {len(recs)} catatan akademik, {len(types)} program studi.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit("Pemakaian: python scripts/load_kaggle.py data/students.csv [jumlah_baris]")
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) == 3 else None)