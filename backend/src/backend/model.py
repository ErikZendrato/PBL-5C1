
from pathlib import Path
import joblib
import pandas as pd

# Menentukan lokasi folder models
BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "models"

# Memuat model yang sudah dilatih
gpa_model = joblib.load(MODEL_DIR / "gpa_model.pkl")
dropout_model = joblib.load(MODEL_DIR / "dropout_model.pkl")


def predict_gpa(student_data: dict):
    """
    Memprediksi GPA semester berikutnya.
    """
    input_data = pd.DataFrame([student_data])

    prediction = gpa_model.predict(input_data)[0]

    return round(float(prediction), 2)


def predict_dropout(student_data: dict):
    """
    Memprediksi kemungkinan dropout.
    """
    input_data = pd.DataFrame([student_data])

    prediction = dropout_model.predict(input_data)[0]
    probability = dropout_model.predict_proba(input_data)[0][1]

    return {
        "dropout_prediction": int(prediction),
        "dropout_probability": round(float(probability), 4),
    }
