import io
import os
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.database import get_supabase, save_prediction
from backend.features import (
    CATEGORY_OPTIONS,
    INTEGER_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURE_RANGES,
)
from backend.model import MAE, get_top_factors, metrics as MODEL_METRICS, predict_gpa


def cors_origins() -> list[str]:
    configured_origins = [
        value.strip()
        for value in os.getenv("CORS_ORIGINS", "").split(",")
        if value.strip()
    ]
    local_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    return list(dict.fromkeys([*configured_origins, *local_origins]))


app = FastAPI(title="Prediksi Performa Mahasiswa API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


class StudentFeatures(BaseModel):
    age: int = Field(ge=15, le=30)
    admission_grade: float = Field(ge=5.5, le=200)
    previous_qualification_grade: float = Field(ge=30.2, le=200)
    gpa_semester_1: float = Field(ge=0, le=4)
    attendance_rate: float = Field(ge=0, le=100)
    assignments_submitted_rate: float = Field(ge=0, le=100)
    library_visits_per_month: int = Field(ge=0, le=30)
    lms_logins_per_week: float = Field(ge=0, le=29.6)
    weekly_work_hours: float = Field(ge=0, le=40)
    missed_deadlines: int = Field(ge=0, le=20)
    commute_time_mins: float = Field(ge=0, le=120)
    sleep_hours: float = Field(ge=4, le=10)
    course_type: Literal[
        "Arts & Humanities",
        "Business",
        "Health Sciences",
        "Law & Social Sciences",
        "STEM",
    ]
    study_mode: Literal["Full-time", "Online", "Part-time"]
    student_id: UUID | None = None
    semester_target: int | None = Field(default=None, ge=1, le=14)


class BatchPrediction(BaseModel):
    students: list[StudentFeatures]


class FollowUpCreate(BaseModel):
    prediction_id: str
    catatan: str = Field(min_length=1)
    status: str = Field(pattern="^(baru|dalam_penanganan|selesai)$")


class FollowUpUpdate(BaseModel):
    catatan: str | None = Field(default=None, min_length=1, max_length=5000)
    status: str | None = Field(
        default=None,
        pattern="^(baru|dalam_penanganan|selesai)$",
    )


class AccountCreate(BaseModel):
    nama: str = Field(min_length=1, max_length=120)
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    role: Literal["admin", "dosen", "mahasiswa"]
    temporary_password: str = Field(min_length=12, max_length=128)


class AccountUpdate(BaseModel):
    nama: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["admin", "dosen", "mahasiswa"] | None = None


class StudentCreate(BaseModel):
    kode_anonim: str = Field(min_length=1, max_length=80)
    prodi: str = Field(min_length=1, max_length=120)
    angkatan: int = Field(ge=2020, le=2100)
    dosen_wali_id: UUID | None = None
    profile_id: UUID | None = None


class StudentUpdate(BaseModel):
    kode_anonim: str | None = Field(default=None, min_length=1, max_length=80)
    prodi: str | None = Field(default=None, min_length=1, max_length=120)
    angkatan: int | None = Field(default=None, ge=2020, le=2100)
    dosen_wali_id: UUID | None = None
    profile_id: UUID | None = None


class StudentPrediction(BaseModel):
    student_id: UUID
    semester_target: int = Field(ge=1, le=14)


ACADEMIC_COLUMNS = [
    "student_id",
    "semester",
    "ips",
    "ipk",
    "sks",
    "kehadiran",
    *MODEL_FEATURES,
]
ACADEMIC_NUMERIC_RANGES = {
    "semester": (1, 14),
    "ips": (0, 4),
    "ipk": (0, 4),
    "sks": (0, 300),
    "kehadiran": (0, 100),
    **NUMERIC_FEATURE_RANGES,
}
ACADEMIC_INTEGER_COLUMNS = {"semester", "sks", *INTEGER_FEATURES}


def prediction_category(value: float) -> str:
    if value >= 3.25:
        return "Baik"
    if value >= 2.50:
        return "Cukup"
    return "Perlu Perhatian"


@app.get("/")
def home():
    return {"message": "API Prediksi Performa Mahasiswa aktif"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(student: StudentFeatures, user=Depends(require_role("admin", "dosen", "mahasiswa"))):
    data = student.model_dump()
    predicted_value = predict_gpa(data)
    lower_bound = max(0.0, predicted_value - MAE)
    upper_bound = min(4.0, predicted_value + MAE)
    result = {
        "nilai_prediksi": predicted_value,
        "batas_bawah": round(lower_bound, 2),
        "batas_atas": round(upper_bound, 2),
        "kategori": prediction_category(predicted_value),
        "faktor": get_top_factors(),
        "penjelasan": (
            "Perkiraan dihitung dari data yang diberikan. Rentang menunjukkan "
            "perkiraan nilai di sekitar hasil model, bukan kepastian."
        ),
    }
    if student.student_id is not None or student.semester_target is not None:
        if student.student_id is None or student.semester_target is None:
            raise HTTPException(
                status_code=422,
                detail="Mahasiswa dan semester target harus diisi bersama.",
            )
        student_row = get_student(str(student.student_id))
        if not student_row or not can_access_student(user, student_row):
            raise HTTPException(
                status_code=404,
                detail="Data mahasiswa tidak ditemukan atau tidak dapat diakses.",
            )
        saved = save_prediction(
            student_id=str(student.student_id),
            semester_target=student.semester_target,
            hasil=result["kategori"],
            nilai_prediksi=predicted_value,
            batas_bawah=result["batas_bawah"],
            batas_atas=result["batas_atas"],
            faktor=result["faktor"],
            model_version="v2.1-kaggle",
            input_features={key: data[key] for key in MODEL_FEATURES},
        )
        if saved:
            result["prediction_id"] = saved[0]["id"]
    return result


@app.post("/predict/batch")
def predict_batch(payload: BatchPrediction, user=Depends(require_role("admin", "dosen"))):
    if len(payload.students) > 500:
        raise HTTPException(status_code=422, detail="Maksimal 500 mahasiswa dalam satu batch.")
    return {"total": len(payload.students), "predictions": [predict(item, user) for item in payload.students]}


def validate_academic_csv(content: bytes):
    try:
        frame = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Berkas CSV tidak dapat dibaca.") from exc

    missing = [column for column in ACADEMIC_COLUMNS if column not in frame.columns]
    extra_errors = []
    if missing:
        extra_errors.append({"baris": 0, "pesan": f"Kolom wajib hilang: {', '.join(missing)}"})
    extra_columns = [column for column in frame.columns if column not in ACADEMIC_COLUMNS]
    if extra_columns:
        extra_errors.append({
            "baris": 0,
            "pesan": f"Kolom tidak dikenal: {', '.join(extra_columns)}",
        })
    if frame.empty:
        extra_errors.append({"baris": 0, "pesan": "CSV harus berisi minimal satu baris data."})

    for index, row in frame.iterrows():
        line = index + 2
        values = row.to_dict()
        student_id = values.get("student_id", "").strip()
        if not student_id:
            extra_errors.append({"baris": line, "pesan": "student_id tidak boleh kosong."})
        else:
            try:
                UUID(student_id)
            except ValueError:
                extra_errors.append({
                    "baris": line,
                    "pesan": "student_id harus berupa UUID mahasiswa yang valid.",
                })
        for column, (minimum, maximum) in ACADEMIC_NUMERIC_RANGES.items():
            raw_value = values.get(column, "").strip()
            try:
                numeric_value = float(raw_value.replace(",", "."))
                if (
                    not minimum <= numeric_value <= maximum
                    or (
                        column in ACADEMIC_INTEGER_COLUMNS
                        and not numeric_value.is_integer()
                    )
                ):
                    raise ValueError()
            except ValueError:
                expected_type = (
                    "bilangan bulat"
                    if column in ACADEMIC_INTEGER_COLUMNS
                    else "angka"
                )
                extra_errors.append({
                    "baris": line,
                    "pesan": (
                        f"{column} harus berupa {expected_type} antara "
                        f"{minimum} sampai {maximum}."
                    ),
                })
        for column, options in CATEGORY_OPTIONS.items():
            if values.get(column, "").strip() not in options:
                extra_errors.append({
                    "baris": line,
                    "pesan": (
                        f"{column} harus salah satu dari: {', '.join(options)}."
                    ),
                })

    columns_for_duplicate = [column for column in ("student_id", "semester") if column in frame.columns]
    if len(columns_for_duplicate) == 2:
        for keys, lines in frame.assign(_baris=frame.index + 2).groupby(columns_for_duplicate, dropna=False):
            if len(lines) > 1:
                student_id, semester = keys
                extra_errors.append({
                    "baris": lines["_baris"].tolist(),
                    "pesan": f"Data duplikat untuk student_id {student_id} pada semester {semester}.",
                })

    return {
        "valid": not extra_errors,
        "total_baris": len(frame),
        "errors": extra_errors,
        "preview": frame.head(10).to_dict(orient="records"),
    }


@app.post("/upload/validate")
def upload_validate(file: UploadFile = File(...), user=Depends(require_role("admin"))):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Berkas harus berformat CSV.")
    return validate_academic_csv(file.file.read())


@app.post("/upload/commit")
def upload_commit(file: UploadFile = File(...), user=Depends(require_role("admin"))):
    content = file.file.read()
    result = validate_academic_csv(content)
    if not result["valid"]:
        raise HTTPException(status_code=422, detail={"pesan": "CSV masih memiliki kesalahan.", "errors": result["errors"]})
    try:
        frame = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
        records = frame.to_dict(orient="records")
        for record in records:
            record["semester"] = int(record["semester"])
            record["ips"] = float(record["ips"])
            record["ipk"] = float(record["ipk"])
            record["sks"] = int(record["sks"])
            record["kehadiran"] = float(record["kehadiran"])
            for column in NUMERIC_FEATURE_RANGES:
                record[column] = (
                    int(record[column])
                    if column in INTEGER_FEATURES
                    else float(record[column].replace(",", "."))
                )
        client = get_supabase()
        student_ids = sorted({record["student_id"] for record in records})
        students_response = (
            client.table("students")
            .select("id")
            .in_("id", student_ids)
            .execute()
        )
        known_student_ids = {row["id"] for row in students_response.data}
        unknown_student_ids = set(student_ids) - known_student_ids
        if unknown_student_ids:
            raise ValueError(f"{len(unknown_student_ids)} student_id tidak ditemukan.")
        client.table("academic_records").upsert(
            records, on_conflict="student_id,semester"
        ).execute()
        prediction_rows = []
        for record in records:
            model_features = {key: record[key] for key in MODEL_FEATURES}
            predicted_value = predict_gpa(model_features)
            lower_bound = round(max(0.0, predicted_value - MAE), 2)
            upper_bound = round(min(4.0, predicted_value + MAE), 2)
            prediction_rows.append({
                "student_id": record["student_id"],
                "semester_target": min(record["semester"] + 1, 14),
                "hasil": prediction_category(predicted_value),
                "probabilitas": None,
                "nilai_prediksi": predicted_value,
                "batas_bawah": lower_bound,
                "batas_atas": upper_bound,
                "faktor": {"items": get_top_factors(), "input_features": model_features},
                "model_version": "v2.1-kaggle",
            })
        client.table("predictions").insert(prediction_rows).execute()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Data akademik mungkin sudah tersimpan, tetapi proses prediksi "
                "tidak selesai. Periksa data sebelum mengunggah ulang."
            ),
        ) from exc
    return {
        "disimpan": len(records),
        "prediksi": len(prediction_rows),
        "pesan": "Data semester dan prediksi berhasil disimpan.",
    }


def get_student(student_id: str) -> dict | None:
    response = (
        get_supabase()
        .table("students")
        .select("*")
        .eq("id", student_id)
        .maybe_single()
        .execute()
    )
    return response.data


def can_access_student(user: dict, student: dict) -> bool:
    if user["role"] == "admin":
        return True
    if user["role"] == "dosen":
        return student.get("dosen_wali_id") == user["sub"]
    return student.get("profile_id") == user["sub"]


def ensure_dosen(user_id: str | None) -> None:
    if user_id and get_supabase().table("profiles").select("id").eq(
        "id", user_id
    ).eq("role", "dosen").maybe_single().execute().data is None:
        raise HTTPException(status_code=422, detail="Dosen wali tidak ditemukan.")


def ensure_mahasiswa(user_id: str | None) -> None:
    if user_id and get_supabase().table("profiles").select("id").eq(
        "id", user_id
    ).eq("role", "mahasiswa").maybe_single().execute().data is None:
        raise HTTPException(status_code=422, detail="Akun mahasiswa tidak ditemukan.")


@app.get("/dashboard/admin")
def admin_dashboard(user=Depends(require_role("admin"))):
    client = get_supabase()
    students_count = client.table("students").select("id", count="exact", head=True).execute().count
    profiles = client.table("profiles").select("role").limit(10000).execute().data
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_predictions = (
        client.table("predictions")
        .select("hasil")
        .gte("created_at", month_start.isoformat())
        .limit(10000)
        .execute()
        .data
    )
    all_predictions = (
        client.table("predictions")
        .select("hasil,student_id,created_at")
        .order("created_at", desc=True)
        .limit(10000)
        .execute()
        .data
    )
    category_counts: dict[str, int] = {}
    for prediction in all_predictions:
        category = prediction["hasil"]
        category_counts[category] = category_counts.get(category, 0) + 1
    students = client.table("students").select("angkatan").limit(10000).execute().data
    cohort_counts: dict[str, int] = {}
    for student in students:
        cohort = str(student["angkatan"])
        cohort_counts[cohort] = cohort_counts.get(cohort, 0) + 1
    return {
        "total_mahasiswa": students_count or 0,
        "total_dosen": sum(profile["role"] == "dosen" for profile in profiles),
        "prediksi_bulan_ini": len(month_predictions),
        "model_metrics": MODEL_METRICS,
        "kategori": category_counts,
        "angkatan": cohort_counts,
        "aktivitas": all_predictions[:10],
    }


@app.get("/admin/predictions")
def admin_predictions(
    limit: int = Query(default=1000, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    user=Depends(require_role("admin")),
):
    client = get_supabase()
    response = (
        client.table("predictions")
        .select(
            "id,student_id,semester_target,hasil,nilai_prediksi,batas_bawah,"
            "batas_atas,model_version,created_at",
            count="exact",
        )
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    predictions = response.data or []
    student_ids = sorted({item["student_id"] for item in predictions})
    students = (
        client.table("students")
        .select("id,kode_anonim")
        .in_("id", student_ids)
        .execute()
        .data
        if student_ids
        else []
    )
    student_codes = {student["id"]: student["kode_anonim"] for student in students}
    return {
        "predictions": [
            {**prediction, "kode_anonim": student_codes.get(prediction["student_id"], "Mahasiswa")}
            for prediction in predictions
        ],
        "total": response.count or 0,
        "limit": limit,
        "offset": offset,
    }


@app.get("/dashboard/dosen")
def lecturer_dashboard(user=Depends(require_role("dosen"))):
    client = get_supabase()
    students = (
        client.table("students")
        .select("*")
        .eq("dosen_wali_id", user["sub"])
        .order("kode_anonim")
        .limit(1000)
        .execute()
        .data
    )
    student_ids = [student["id"] for student in students]
    predictions = (
        client.table("predictions")
        .select("*")
        .in_("student_id", student_ids)
        .order("created_at", desc=True)
        .limit(1000)
        .execute()
        .data
        if student_ids
        else []
    )
    category_counts: dict[str, int] = {}
    for prediction in predictions:
        category = prediction["hasil"]
        category_counts[category] = category_counts.get(category, 0) + 1
    return {
        "students": students,
        "predictions": predictions,
        "kategori": category_counts,
        "prioritas": sorted(
            (item for item in predictions if item["hasil"] == "Perlu Perhatian"),
            key=lambda item: item["nilai_prediksi"],
        )[:10],
    }


@app.get("/dashboard/mahasiswa")
def student_dashboard(user=Depends(require_role("mahasiswa"))):
    response = (
        get_supabase()
        .table("students")
        .select("*")
        .eq("profile_id", user["sub"])
        .maybe_single()
        .execute()
    )
    if not response.data:
        return {"student": None, "records": [], "predictions": [], "follow_ups": []}
    student = response.data
    records = (
        get_supabase()
        .table("academic_records")
        .select("*")
        .eq("student_id", student["id"])
        .order("semester")
        .execute()
        .data
    )
    predictions = (
        get_supabase()
        .table("predictions")
        .select("*")
        .eq("student_id", student["id"])
        .order("semester_target")
        .execute()
        .data
    )
    follow_ups = list_followups_for_student(student["id"])
    return {
        "student": student,
        "records": records,
        "predictions": predictions,
        "follow_ups": follow_ups,
    }


@app.get("/students")
def list_students(user=Depends(require_role("admin", "dosen", "mahasiswa"))):
    query = get_supabase().table("students").select("*").order("kode_anonim")
    if user["role"] == "dosen":
        query = query.eq("dosen_wali_id", user["sub"])
    elif user["role"] == "mahasiswa":
        query = query.eq("profile_id", user["sub"])
    return {"students": query.limit(1000).execute().data}


@app.post("/admin/students")
def create_student(
    payload: StudentCreate,
    user=Depends(require_role("admin")),
):
    ensure_dosen(str(payload.dosen_wali_id) if payload.dosen_wali_id else None)
    ensure_mahasiswa(str(payload.profile_id) if payload.profile_id else None)
    try:
        result = get_supabase().table("students").insert(
            payload.model_dump(mode="json")
        ).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Data mahasiswa tidak dapat dibuat. Periksa kode dan akun yang terhubung.",
        ) from exc
    return {"student": result.data[0]}


@app.patch("/admin/students/{student_id}")
def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    user=Depends(require_role("admin")),
):
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Tidak ada perubahan untuk disimpan.")
    if "dosen_wali_id" in updates:
        ensure_dosen(updates["dosen_wali_id"])
    if "profile_id" in updates:
        ensure_mahasiswa(updates["profile_id"])
    result = (
        get_supabase()
        .table("students")
        .update(updates)
        .eq("id", str(student_id))
        .execute()
        .data
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data mahasiswa tidak ditemukan.")
    return {"student": result[0]}


@app.delete("/admin/students/{student_id}")
def delete_student(
    student_id: UUID,
    user=Depends(require_role("admin")),
):
    result = (
        get_supabase()
        .table("students")
        .delete()
        .eq("id", str(student_id))
        .execute()
        .data
    )
    if not result:
        raise HTTPException(status_code=404, detail="Data mahasiswa tidak ditemukan.")
    return {"dihapus": True}


@app.get("/admin/accounts")
def list_accounts(user=Depends(require_role("admin"))):
    client = get_supabase()
    profiles = client.table("profiles").select("id,nama,role").limit(10000).execute().data
    try:
        users_response = client.auth.admin.list_users()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Akun tidak dapat dimuat saat ini.") from exc
    auth_users = getattr(users_response, "users", users_response)
    email_by_id = {str(auth_user.id): auth_user.email for auth_user in auth_users}
    return {
        "accounts": [
            {**profile, "email": email_by_id.get(profile["id"])}
            for profile in profiles
        ]
    }


@app.post("/admin/accounts")
def create_account(payload: AccountCreate, user=Depends(require_role("admin"))):
    client = get_supabase()
    try:
        created = client.auth.admin.create_user({
            "email": payload.email,
            "password": payload.temporary_password,
            "email_confirm": True,
            "user_metadata": {"nama": payload.nama},
        })
        auth_user = getattr(created, "user", created)
        client.table("profiles").insert({
            "id": str(auth_user.id),
            "nama": payload.nama,
            "role": payload.role,
        }).execute()
    except Exception as exc:
        auth_user = locals().get("auth_user")
        if auth_user is not None:
            try:
                client.auth.admin.delete_user(str(auth_user.id))
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Akun dibuat tetapi profil gagal disiapkan; admin perlu memeriksa Supabase Auth.",
                ) from exc
        raise HTTPException(
            status_code=422,
            detail="Akun tidak dapat dibuat. Periksa email yang belum digunakan dan kata sandi sementara.",
        ) from exc
    return {
        "account": {
            "id": str(auth_user.id),
            "nama": payload.nama,
            "email": payload.email,
            "role": payload.role,
        }
    }


@app.patch("/admin/accounts/{user_id}")
def update_account(
    user_id: UUID,
    payload: AccountUpdate,
    user=Depends(require_role("admin")),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Tidak ada perubahan untuk disimpan.")
    result = (
        get_supabase()
        .table("profiles")
        .update(updates)
        .eq("id", str(user_id))
        .execute()
        .data
    )
    if not result:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
    return {"account": result[0]}


@app.delete("/admin/accounts/{user_id}")
def delete_account(
    user_id: UUID,
    user=Depends(require_role("admin")),
):
    if str(user_id) == user["sub"]:
        raise HTTPException(status_code=422, detail="Akun admin yang sedang digunakan tidak dapat dihapus.")
    client = get_supabase()
    profile = client.table("profiles").select("id").eq("id", str(user_id)).maybe_single().execute().data
    if not profile:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
    try:
        client.table("students").update({"profile_id": None}).eq("profile_id", str(user_id)).execute()
        client.auth.admin.delete_user(str(user_id))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Akun tidak dapat dihapus saat ini.") from exc
    return {"dihapus": True}


@app.get("/model/info")
def model_info(user=Depends(require_role("admin", "dosen", "mahasiswa"))):
    response = get_supabase().table("model_versions").select("*").order("tanggal", desc=True).limit(10).execute()
    return {
        "active": {
            "versi": "v2.1-kaggle",
            "algoritma": "LinearRegression",
            "metrik": MODEL_METRICS,
            "features": get_top_factors(limit=20),
        },
        "versions": response.data,
    }


@app.get("/students/{student_id}/history")
def student_history(student_id: str, user=Depends(require_role("admin", "dosen", "mahasiswa"))):
    student = get_student(student_id)
    if not student or not can_access_student(user, student):
        raise HTTPException(status_code=404, detail="Data mahasiswa tidak ditemukan atau tidak dapat diakses.")
    records = get_supabase().table("academic_records").select("*").eq("student_id", student_id).order("semester").execute()
    predictions = get_supabase().table("predictions").select("*").eq("student_id", student_id).order("semester_target").execute()
    follow_ups = list_followups_for_student(student_id)
    return {
        "student": student,
        "records": records.data,
        "predictions": predictions.data,
        "follow_ups": follow_ups,
    }


def list_followups_for_student(student_id: str) -> list[dict]:
    predictions = (
        get_supabase()
        .table("predictions")
        .select("id")
        .eq("student_id", student_id)
        .execute()
        .data
    )
    prediction_ids = [prediction["id"] for prediction in predictions]
    if not prediction_ids:
        return []
    return (
        get_supabase()
        .table("follow_ups")
        .select("*")
        .in_("prediction_id", prediction_ids)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@app.get("/follow-ups")
def list_followups(user=Depends(require_role("admin", "dosen", "mahasiswa"))):
    client = get_supabase()
    query = client.table("follow_ups").select("*").order("created_at", desc=True)
    if user["role"] == "dosen":
        query = query.eq("dosen_id", user["sub"])
    elif user["role"] == "mahasiswa":
        student = (
            client.table("students")
            .select("id")
            .eq("profile_id", user["sub"])
            .maybe_single()
            .execute()
            .data
        )
        return {
            "follow_ups": list_followups_for_student(student["id"]) if student else []
        }
    return {"follow_ups": query.limit(1000).execute().data}


@app.post("/follow-ups")
def create_followup(payload: FollowUpCreate, user=Depends(require_role("admin", "dosen"))):
    prediction = (
        get_supabase()
        .table("predictions")
        .select("id,student_id")
        .eq("id", payload.prediction_id)
        .maybe_single()
        .execute()
        .data
    )
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediksi tidak ditemukan.")
    student = get_student(prediction["student_id"])
    if not student or not can_access_student(user, student):
        raise HTTPException(status_code=404, detail="Prediksi tidak ditemukan.")
    row = {"prediction_id": payload.prediction_id, "dosen_id": user["sub"], "catatan": payload.catatan, "status": payload.status}
    try:
        data = get_supabase().table("follow_ups").insert(row).execute().data
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Catatan tindak lanjut tidak dapat disimpan.") from exc
    return {"follow_up": data[0]}


@app.patch("/follow-ups/{follow_up_id}")
def update_followup(
    follow_up_id: UUID,
    payload: FollowUpUpdate,
    user=Depends(require_role("admin", "dosen")),
):
    follow_up = (
        get_supabase()
        .table("follow_ups")
        .select("*")
        .eq("id", str(follow_up_id))
        .maybe_single()
        .execute()
        .data
    )
    if not follow_up or (
        user["role"] == "dosen" and follow_up["dosen_id"] != user["sub"]
    ):
        raise HTTPException(status_code=404, detail="Catatan tindak lanjut tidak ditemukan.")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Tidak ada perubahan untuk disimpan.")
    updates["updated_at"] = datetime.now(UTC).isoformat()
    updated = (
        get_supabase()
        .table("follow_ups")
        .update(updates)
        .eq("id", str(follow_up_id))
        .execute()
        .data
    )
    return {"follow_up": updated[0]}
