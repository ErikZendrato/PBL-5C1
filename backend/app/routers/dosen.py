from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import get_db
from ..deps import User, require
from ..utils import fetch_all, one, read_csv

router = APIRouter(prefix="/dosen", tags=["dosen"])
dosen_only = require("dosen")


def db():
    return get_db()


def own_assignment(aid: int, user: User) -> dict:
    rows = (db().table("course_assignments")
            .select("*,courses(code,name,credits),semesters(code)")
            .eq("id", aid).eq("lecturer_id", user.id).execute().data)
    if not rows:
        raise HTTPException(404, "Mata kuliah tidak ditemukan atau bukan milik Anda")
    return rows[0]


def class_enrollments(a: dict):
    return fetch_all("enrollments", "id,students(student_number,full_name),course_grades(letter,status)",
                     course_id=a["course_id"], semester_id=a["semester_id"])


@router.get("/courses")
def my_courses(user: User = Depends(dosen_only)):
    asg = (db().table("course_assignments").select("*,courses(code,name,credits),semesters(code,sort_order)")
           .eq("lecturer_id", user.id).execute().data)
    out = []
    for a in asg:
        enr = class_enrollments(a)
        final = sum(1 for e in enr if (one(e.get("course_grades")) or {}).get("status") == "final")
        out.append({"id": a["id"], "course": a["courses"], "semester": a["semesters"]["code"],
                    "sort_order": a["semesters"]["sort_order"], "total": len(enr), "final": final})
    return sorted(out, key=lambda x: -x["sort_order"])


@router.get("/courses/{aid}/grades")
def class_grades(aid: int, user: User = Depends(dosen_only)):
    a = own_assignment(aid, user)
    rows = []
    for e in class_enrollments(a):
        cg = one(e.get("course_grades")) or {}
        rows.append({"enrollment_id": e["id"], "student_number": e["students"]["student_number"],
                     "name": e["students"]["full_name"], "letter": cg.get("letter"),
                     "status": cg.get("status", "kosong")})
    rows.sort(key=lambda r: r["student_number"])
    return {"course": a["courses"], "semester": a["semesters"]["code"], "rows": rows}


class GradeItem(BaseModel):
    enrollment_id: int
    letter: str | None = None


class GradeBody(BaseModel):
    items: list[GradeItem]


def save_draft(a: dict, user: User, items: list[GradeItem]):
    letters = {r["letter"] for r in fetch_all("grade_scale", "letter")}
    enr = {e["id"]: e for e in class_enrollments(a)}
    saved, errors, upserts, deletes = 0, [], [], []
    for it in items:
        e = enr.get(it.enrollment_id)
        if not e:
            errors.append(f"Enrollment {it.enrollment_id} bukan bagian kelas ini")
            continue
        cg = one(e.get("course_grades")) or {}
        if cg.get("status") == "final":
            errors.append(f"{e['students']['full_name']}: nilai sudah final")
            continue
        letter = (it.letter or "").strip().upper()
        if not letter:
            deletes.append(it.enrollment_id)
        elif letter not in letters:
            errors.append(f"{e['students']['full_name']}: nilai '{letter}' tidak dikenal")
        else:
            upserts.append({"enrollment_id": it.enrollment_id, "letter": letter,
                            "status": "draft", "entered_by": user.id})
    if upserts:
        db().table("course_grades").upsert(upserts, on_conflict="enrollment_id").execute()
        saved += len(upserts)
    if deletes:
        db().table("course_grades").delete().in_("enrollment_id", deletes).eq("status", "draft").execute()
    return {"saved": saved, "errors": errors}


@router.put("/courses/{aid}/grades")
def save_grades(aid: int, body: GradeBody, user: User = Depends(dosen_only)):
    return save_draft(own_assignment(aid, user), user, body.items)


@router.post("/courses/{aid}/grades/import")
async def import_grades(aid: int, file: UploadFile, user: User = Depends(dosen_only)):
    """CSV dengan kolom: student_number, letter"""
    a = own_assignment(aid, user)
    by_number = {e["students"]["student_number"]: e["id"] for e in class_enrollments(a)}
    items, errors = [], []
    for i, r in enumerate(await read_csv(file), start=2):
        eid = by_number.get(r.get("student_number", ""))
        if eid is None:
            errors.append(f"Baris {i}: ID '{r.get('student_number', '')}' tidak terdaftar di kelas ini")
        else:
            items.append(GradeItem(enrollment_id=eid, letter=r.get("letter", "")))
    res = save_draft(a, user, items)
    res["errors"] = errors + res["errors"]
    return res


@router.post("/courses/{aid}/finalize")
def finalize(aid: int, user: User = Depends(dosen_only)):
    a = own_assignment(aid, user)
    enr = class_enrollments(a)
    if not enr:
        raise HTTPException(400, "Belum ada mahasiswa terdaftar di kelas ini")
    missing = [e["students"]["full_name"] for e in enr if not (one(e.get("course_grades")) or {}).get("letter")]
    if missing:
        raise HTTPException(400, "Nilai belum lengkap untuk: " + ", ".join(missing[:10]))
    ids = [e["id"] for e in enr]
    db().table("course_grades").update({"status": "final"}).in_("enrollment_id", ids).eq("status", "draft").execute()
    # Hitung IP/IPK otomatis untuk mahasiswa yang SEMUA mata kuliah semesternya sudah final
    computed = db().rpc("compute_semester_records", {"p_semester_id": a["semester_id"]}).execute().data
    return {"finalized": len(ids), "records_computed": computed}
