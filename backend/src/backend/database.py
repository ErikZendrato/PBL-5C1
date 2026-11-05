from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import os

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Konfigurasi Supabase belum lengkap.")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


def save_prediction(
    prediction_type: str,
    input_features: dict,
    predicted_value: float = None,
    predicted_class: int = None,
    dropout_probability: float = None,
):
    data = {
        "prediction_type": prediction_type,
        "input_features": input_features,
        "predicted_value": predicted_value,
        "predicted_class": predicted_class,
        "dropout_probability": dropout_probability,
    }

    response = (
        supabase
        .table("predictions")
        .insert(data)
        .execute()
    )

    return response.data

def get_predictions(limit: int = 50):
    response = (
        supabase
        .table("predictions")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data
