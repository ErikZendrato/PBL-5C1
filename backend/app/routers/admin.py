from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import get_db
from ..deps import User, require
from ..utils import chunks, fetch_all, one, read_csv

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require("admin")

FIELDS = {
    "academic_programs": ["code", "name"],
    "students": ["profile_id", "student_number", "full_name", "program_id", "entry_year",
                 "advisor_id", "show_prediction"],
    "semesters": ["code", "academic_year", "term", "sort_order", "is_active"],
    "courses": ["code", "name", "credits", "program_id"],
    "course_assignments": ["lecturer_id", "course_id", "semester_id"],
    "enrollments": ["student_id", "course_id", "semester_id"],
}
SELECTS = {
    "students": "*,academic_programs(code,name)",
    "courses": "*,academic_programs(code)",
    "course_assignments": "*,courses(code,name),semesters(code),profiles(full_name)",
    "enrollments": "*,students(student_number,full_name),courses(code,name),semesters(code)",
}


def db():
    return get_db()


def check_table(table: str):
    if table not in FIELDS:
        raise HTTPException(404, "Tabel tidak dikenal")


def clean(table: str, body: dict) -> dict:
    return {k: (None if body[k] == "" else body[k]) for k in FIELDS[table] if k in body}


def run(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as e:  # pesan galat dari database dikembalikan apa adanya
        raise HTTPException(400, getattr(e, "message", None) or str(e))


# ---------- CRUD data induk ----------
@router.get("/tables/{table}")
def list_rows(table: str, limit: int = 1000, user: User = Depends(admin_only)):
    check_table(table)
    return run(lambda: db().table(table).select(SELECTS.get(table, "*"))
               .order("id", desc=True).limit(min(limit, 5000)).execute().data)


@router.post("/tables/{table}")
def create_row(table: str, body: dict, user: User = Depends(admin_only)):
    check_table(table)
    return run(lambda: db().table(table).insert(clean(table, body)).execute().data[0])


@router.patch("/tables/{table}/{rid}")
def update_row(table: str, rid: int, body: dict, user: User = Depends(admin_only)):
    check_table(table)
    return run(lambda: db().table(table).update(clean(table, body)).eq("id", rid).execute().data)


@router.delete("/tables/{table}/{rid}")
def delete_row(table: str, rid: int, user: User = Depends(admin_only)):
    check_table(table)
    run(lambda: db().table(table).delete().eq("id", rid).execute())
    return {"ok": True}


# ---------- Pengguna ----------
class NewUser(BaseModel):
    email: str
    password: str
    full_name: str
    role: str


@router.get("/users")
def list_users(user: User = Depends(admin_only)):
    profiles = fetch_all("profiles", "id,full_name,role,is_active")
    emails = {u.id: u.email for u in db().auth.admin.list_users(per_page=1000)}
    return [{**p, "email": emails.get(p["id"], "")} for p in profiles]


@router.post("/users")
def create_user(body: NewUser, user: User = Depends(admin_only)):
    if body.role not in ("admin", "dosen", "mahasiswa"):
        raise HTTPException(400, "Peran tidak valid")
    created = run(lambda: db().auth.admin.create_user(
        {"email": body.email, "password": body.password, "email_confirm": True}))
    uid = created.user.id
    try:
        db().table("profiles").insert({"id": uid, "full_name": body.full_name, "role": body.role}).execute()
    except Exception as e:
        db().auth.admin.delete_user(uid)
        raise HTTPException(400, str(e))
    return {"id": uid}


@router.patch("/users/{uid}")
def update_user(uid: str, body: dict, user: User = Depends(admin_only)):
    allowed = {k: body[k] for k in ("full_name", "role", "is_active") if k in body}
    return run(lambda: db().table("profiles").update(allowed).eq("id", uid).execute().data)


# ---------- Impor CSV ----------
def recompute(semester_ids):
    for sid in semester_ids:
        db().rpc("compute_semester_records", {"p_semester_id": sid}).execute()


@router.post("/import/{kind}")
async def import_csv(kind: str, file: UploadFile, user: User = Depends(admin_only)):
    """kind:
    students       -> student_number, full_name, program_code, entry_year
    courses        -> code, name, credits, program_code (opsional)
    grades_history -> student_number, course_code, semester_code, letter  (nilai historis, langsung final)
    """
    rows = await read_csv(file)
    errors: list[str] = []
    programs = {p["code"]: p["id"] for p in fetch_all("academic_programs", "id,code")}

    if kind == "students":
        payload = []
        for i, r in enumerate(rows, start=2):
            pid = programs.get(r.get("program_code", ""))
            if not r.get("student_number") or not r.get("full_name") or pid is None or not r.get("entry_year", "").isdigit():
                errors.append(f"Baris {i}: kolom wajib kosong, kode prodi tidak dikenal, atau angkatan bukan angka")
                continue
            payload.append({"student_number": r["student_number"], "full_name": r["full_name"],
                            "program_id": pid, "entry_year": int(r["entry_year"])})
        for part in chunks(payload):
            db().table("students").upsert(part, on_conflict="student_number").execute()
        return {"inserted": len(payload), "errors": errors[:50], "error_count": len(errors)}

    if kind == "courses":
        payload = []
        for i, r in enumerate(rows, start=2):
            if not r.get("code") or not r.get("name") or not r.get("credits", "").isdigit():
                errors.append(f"Baris {i}: kode, nama, atau SKS tidak valid")
                continue
            payload.append({"code": r["code"], "name": r["name"], "credits": int(r["credits"]),
                            "program_id": programs.get(r.get("program_code", ""))})
        for part in chunks(payload):
            db().table("courses").upsert(part, on_conflict="code").execute()
        return {"inserted": len(payload), "errors": errors[:50], "error_count": len(errors)}

    if kind == "grades_history":
        students = {s["student_number"]: s["id"] for s in fetch_all("students", "id,student_number")}
        courses = {c["code"]: c["id"] for c in fetch_all("courses", "id,code")}
        sems = {s["code"]: s["id"] for s in fetch_all("semesters", "id,code")}
        letters = {g["letter"] for g in fetch_all("grade_scale", "letter")}
        good = []
        for i, r in enumerate(rows, start=2):
            s, c, m, l = (students.get(r.get("student_number", "")), courses.get(r.get("course_code", "")),
                          sems.get(r.get("semester_code", "")), r.get("letter", "").upper())
            if s is None or c is None or m is None or l not in letters:
                errors.append(f"Baris {i}: ID mahasiswa, kode mata kuliah, kode semester, atau nilai tidak dikenal")
                continue
            good.append((s, c, m, l))
        enr_rows = [{"student_id": s, "course_id": c, "semester_id": m} for s, c, m, _ in good]
        for part in chunks(enr_rows):
            db().table("enrollments").upsert(part, on_conflict="student_id,course_id,semester_id").execute()
        enr_id = {(e["student_id"], e["course_id"], e["semester_id"]): e["id"]
                  for e in fetch_all("enrollments", "id,student_id,course_id,semester_id")}
        existing = {g["enrollment_id"]: g for g in fetch_all("course_grades", "enrollment_id,letter,status")}
        now = datetime.now(timezone.utc).isoformat()
        new_rows, skipped = [], 0
        for s, c, m, l in good:
            eid = enr_id[(s, c, m)]
            old = existing.get(eid)
            if old and old["status"] == "final":
                if old["letter"] != l:
                    errors.append(f"Enrollment {eid}: sudah final dengan nilai {old['letter']}, gunakan koreksi nilai")
                skipped += 1
                continue
            new_rows.append({"enrollment_id": eid, "letter": l, "status": "final",
                             "entered_by": user.id, "finalized_at": now})
        for part in chunks(new_rows):
            db().table("course_grades").upsert(part, on_conflict="enrollment_id").execute()
        recompute({m for _, _, m, _ in good})
        return {"inserted": len(new_rows), "skipped": skipped, "errors": errors[:50], "error_count": len(errors)}

    raise HTTPException(404, "Jenis impor tidak dikenal")


# ---------- Koreksi nilai final, kelengkapan, audit ----------
class OverrideBody(BaseModel):
    letter: str


@router.put("/grades/{enrollment_id}")
def override_grade(enrollment_id: int, body: OverrideBody, user: User = Depends(admin_only)):
    letter = body.letter.strip().upper()
    if letter not in {g["letter"] for g in fetch_all("grade_scale", "letter")}:
        raise HTTPException(400, "Nilai tidak dikenal")
    enr = one(db().table("enrollments").select("semester_id").eq("id", enrollment_id).execute().data)
    if not enr:
        raise HTTPException(404, "Enrollment tidak ditemukan")
    db().rpc("admin_override_grade", {"p_enrollment_id": enrollment_id, "p_letter": letter,
                                      "p_actor": user.id}).execute()
    recompute([enr["semester_id"]])
    return {"ok": True}


@router.get("/completeness")
def completeness(semester_id: int, user: User = Depends(admin_only)):
    rows = fetch_all("semester_completeness", "*", semester_id=semester_id)
    courses = {c["id"]: c for c in fetch_all("courses", "id,code,name")}
    names = {p["id"]: p["full_name"] for p in fetch_all("profiles", "id,full_name")}
    return [{"course": courses[r["course_id"]], "lecturer": names.get(r["lecturer_id"], "-"),
             "total": r["total_students"], "final": r["final_grades"], "complete": r["is_complete"]}
            for r in rows]


@router.get("/audit")
def audit(user: User = Depends(admin_only)):
    return (db().table("audit_logs").select("*,profiles(full_name)")
            .order("id", desc=True).limit(300).execute().data)
