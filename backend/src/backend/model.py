
from pathlib import Path
import json

import joblib
import pandas as pd
from backend.features import prepare_model_features

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "models" / "linear_regression_v2_1" / "model.pkl"
METRICS_PATH = MODEL_PATH.parent / "metrics.json"
FEATURE_IMPORTANCE_PATH = MODEL_PATH.parent / "feature_importance.json"
gpa_model = joblib.load(MODEL_PATH)
with METRICS_PATH.open(encoding="utf-8") as metrics_file:
    metrics = json.load(metrics_file)
with FEATURE_IMPORTANCE_PATH.open(encoding="utf-8") as importance_file:
    feature_importance = json.load(importance_file)
MAE = float(metrics["mae"])

FEATURE_LABELS = {
    "age": "Usia",
    "admission_grade": "Nilai saat masuk",
    "previous_qualification_grade": "Nilai pendidikan sebelumnya",
    "gpa_semester_1": "Nilai semester sebelumnya",
    "attendance_rate": "Kehadiran",
    "assignments_submitted_rate": "Tugas yang dikumpulkan",
    "library_visits_per_month": "Kunjungan ke perpustakaan",
    "lms_logins_per_week": "Aktivitas belajar daring",
    "weekly_work_hours": "Jam kerja per minggu",
    "missed_deadlines": "Tugas terlambat",
    "commute_time_mins": "Waktu perjalanan",
    "sleep_hours": "Jam tidur",
}


def predict_gpa(student_data: dict) -> float:
    input_data = pd.DataFrame([prepare_model_features(student_data)])
    prediction = float(gpa_model.predict(input_data)[0])
    return round(min(4.0, max(0.0, prediction)), 2)


def get_top_factors(limit: int = 5) -> list[dict[str, str | float]]:
    result = []
    for item in feature_importance[:limit]:
        name = str(item["feature"]).split("__", maxsplit=1)[-1]
        if name.startswith("course_type_"):
            label = f"Program studi {name.removeprefix('course_type_')}"
        elif name.startswith("study_mode_"):
            label = f"Mode kuliah {name.removeprefix('study_mode_')}"
        else:
            label = FEATURE_LABELS.get(name, name)
        direction = str(item["direction"])
        result.append({
            "faktor": label,
            "arah": direction,
            "coefficient": float(item["coefficient"]),
            "penjelasan": (
                "Nilai ini berkaitan dengan perkiraan yang lebih tinggi."
                if direction == "naik"
                else "Nilai ini berkaitan dengan perkiraan yang lebih rendah."
            ),
        })
    return result
