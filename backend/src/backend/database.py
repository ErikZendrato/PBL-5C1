from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import os

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SECRET_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)


def get_supabase() -> Client:
    if supabase is None:
        raise RuntimeError("Konfigurasi Supabase belum lengkap.")
    return supabase


def get_user_role(user_id: str) -> str | None:
    response = get_supabase().table("profiles").select("role").eq("id", user_id).maybe_single().execute()
    return response.data.get("role") if response.data else None


def save_prediction(
    student_id: str,
    semester_target: int,
    hasil: str,
    nilai_prediksi: float,
    batas_bawah: float,
    batas_atas: float,
    faktor: list[dict],
    model_version: str,
    input_features: dict,
):
    data = {
        "student_id": student_id,
        "semester_target": semester_target,
        "hasil": hasil,
        "probabilitas": None,
        "nilai_prediksi": nilai_prediksi,
        "batas_bawah": batas_bawah,
        "batas_atas": batas_atas,
        "faktor": {"items": faktor, "input_features": input_features},
        "model_version": model_version,
    }
    return get_supabase().table("predictions").insert(data).execute().data

def get_predictions(limit: int = 50):
    response = (
        get_supabase()
        .table("predictions")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data
