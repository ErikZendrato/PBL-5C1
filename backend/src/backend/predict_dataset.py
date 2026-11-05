
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = BASE_DIR / "data" / "student_performance.csv"
MODEL_DIR = BASE_DIR / "models"
OUTPUT_PATH = BASE_DIR / "data" / "prediction_results.csv"

# Membaca dataset
df = pd.read_csv(DATA_PATH)

# Memuat model yang sudah dilatih
gpa_model = joblib.load(MODEL_DIR / "gpa_model.pkl")
dropout_model = joblib.load(MODEL_DIR / "dropout_model.pkl")

# Fitur yang digunakan saat training
numeric_features = [
    "age",
    "admission_grade",
    "previous_qualification_grade",
    "gpa_semester_1",
    "attendance_rate",
    "assignments_submitted_rate",
    "library_visits_per_month",
    "lms_logins_per_week",
    "weekly_work_hours",
    "missed_deadlines",
    "commute_time_mins",
    "sleep_hours",
]

categorical_features = [
    "course_type",
    "study_mode",
]

features = numeric_features + categorical_features

# Mengambil fitur dari seluruh dataset
X = df[features]

# Melakukan prediksi
df["predicted_gpa"] = gpa_model.predict(X).round(2)

df["predicted_dropout"] = dropout_model.predict(X)

df["dropout_probability"] = (
    dropout_model.predict_proba(X)[:, 1].round(4)
)

# Mengubah hasil klasifikasi menjadi teks
df["dropout_status"] = df["predicted_dropout"].map({
    0: "Tidak Berisiko",
    1: "Berisiko"
})

# Menyimpan seluruh hasil
df.to_csv(OUTPUT_PATH, index=False)

print("Prediksi selesai!")
print(f"Jumlah data: {len(df)}")
print(f"File hasil: {OUTPUT_PATH}")

print("\nRingkasan prediksi dropout:")
print(df["dropout_status"].value_counts())

print("\nContoh hasil prediksi:")
print(
    df[
        [
            "gpa_semester_2",
            "predicted_gpa",
            "dropout_status",
            "dropout_probability",
        ]
    ].head(10)
)
