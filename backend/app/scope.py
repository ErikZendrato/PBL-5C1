from fastapi import HTTPException

from .deps import User
from .utils import fetch_all


def visible_student_ids(user: User):
    """None = semua mahasiswa (Admin). Set id = mahasiswa yang boleh dilihat Dosen.
    Aturan sementara: dosen wali, atau dosen yang mengampu salah satu mata kuliah mahasiswa.
    Ubah fungsi ini jika keputusan kampus berbeda (misalnya hanya dosen wali)."""
    if user.role == "admin":
        return None
    if user.role != "dosen":
        raise HTTPException(403, "Tidak berwenang")
    ids = {s["id"] for s in fetch_all("students", "id", advisor_id=user.id)}
    pairs = {(a["course_id"], a["semester_id"])
             for a in fetch_all("course_assignments", "course_id,semester_id", lecturer_id=user.id)}
    if pairs:
        for e in fetch_all("enrollments", "student_id,course_id,semester_id"):
            if (e["course_id"], e["semester_id"]) in pairs:
                ids.add(e["student_id"])
    return ids


def assert_student_access(user: User, student_id: int):
    ids = visible_student_ids(user)
    if ids is not None and student_id not in ids:
        raise HTTPException(403, "Mahasiswa di luar kewenangan Anda")
