from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parents[2]
TRAIN_PATH = BASE_DIR / "data" / "train.csv"
TEST_PATH = BASE_DIR / "data" / "test.csv"
MODEL_DIR = BASE_DIR / "models"
OUTPUT_DIR = MODEL_DIR / "linear_regression_v2_1"
SEED_PATH = BASE_DIR.parent / "supabase" / "seed_model_linear_v2_1.sql"
MODEL_PATH = OUTPUT_DIR / "model.pkl"
METRICS_PATH = OUTPUT_DIR / "metrics.json"
IMPORTANCE_PATH = OUTPUT_DIR / "feature_importance.json"

NUMERIC_FEATURES = [
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
CATEGORICAL_FEATURES = ["course_type", "study_mode"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
GPA_TARGET = "gpa_semester_2"


def create_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def validate_data(train_data: pd.DataFrame, test_data: pd.DataFrame) -> None:
    required_columns = set(FEATURES + [GPA_TARGET])
    for label, data in (("train.csv", train_data), ("test.csv", test_data)):
        missing_columns = sorted(required_columns - set(data.columns))
        if missing_columns:
            raise ValueError(
                f"Kolom wajib tidak ada di {label}: {', '.join(missing_columns)}"
            )
        if data[FEATURES + [GPA_TARGET]].isna().any().any():
            raise ValueError(f"Data fitur/target kosong ditemukan di {label}.")

    if "person_id" in train_data.columns and "person_id" in test_data.columns:
        overlap = set(train_data["person_id"]) & set(test_data["person_id"])
        if overlap:
            raise ValueError(
                f"Ada {len(overlap)} person_id yang tumpang tindih "
                "antara train.csv dan test.csv."
            )


def create_seed_sql(metrics: dict[str, float]) -> str:
    metrics_json = json.dumps(metrics, separators=(",", ":"), sort_keys=True)
    escaped_metrics = metrics_json.replace("'", "''")
    return (
        "-- Seed versi model hasil pelatihan train_v2.py; "
        "jalankan secara manual setelah ditinjau.\n"
        "insert into public.model_versions (versi, algoritma, metrik, tanggal)\n"
        f"values ('v2.1-kaggle', 'LinearRegression', "
        f"'{escaped_metrics}'::jsonb, '{date.today().isoformat()}')\n"
        "on conflict (versi) do update set\n"
        "  algoritma = excluded.algoritma,\n"
        "  metrik = excluded.metrik,\n"
        "  tanggal = excluded.tanggal;\n"
    )


def main() -> None:
    output_paths = [MODEL_PATH, METRICS_PATH, IMPORTANCE_PATH, SEED_PATH]
    existing_outputs = [str(path) for path in output_paths if path.exists()]
    if existing_outputs:
        raise FileExistsError(
            "Tidak menimpa artefak v2 yang sudah ada: "
            + ", ".join(existing_outputs)
        )
    if not TRAIN_PATH.is_file() or not TEST_PATH.is_file():
        raise FileNotFoundError("Jalankan split_data.py untuk membuat train/test.")

    train_data = pd.read_csv(TRAIN_PATH)
    test_data = pd.read_csv(TEST_PATH)
    validate_data(train_data, test_data)
    X_train = train_data[FEATURES]
    X_test = test_data[FEATURES]

    gpa_model = Pipeline(
        steps=[
            ("preprocessing", create_preprocessor()),
            ("model", LinearRegression()),
        ]
    )
    gpa_model.fit(X_train, train_data[GPA_TARGET])
    gpa_predictions = gpa_model.predict(X_test)
    metrics = {
        "mae": float(mean_absolute_error(test_data[GPA_TARGET], gpa_predictions)),
        "rmse": float(
            mean_squared_error(test_data[GPA_TARGET], gpa_predictions) ** 0.5
        ),
        "r2": float(r2_score(test_data[GPA_TARGET], gpa_predictions)),
    }

    feature_names = gpa_model.named_steps["preprocessing"].get_feature_names_out()
    transformed_train = gpa_model.named_steps["preprocessing"].transform(X_train)
    if hasattr(transformed_train, "toarray"):
        transformed_train = transformed_train.toarray()
    feature_standard_deviations = np.std(transformed_train, axis=0)
    raw_coefficients = gpa_model.named_steps["model"].coef_
    standardized_coefficients = raw_coefficients * feature_standard_deviations
    feature_importance = []
    for feature_name, raw_coefficient, coefficient in zip(
        feature_names,
        raw_coefficients,
        standardized_coefficients,
        strict=True,
    ):
        feature_importance.append({
            "feature": str(feature_name),
            "coefficient": float(coefficient),
            "model_coefficient": float(raw_coefficient),
            "direction": "naik" if coefficient > 0 else "turun",
            "absolute_coefficient": abs(float(coefficient)),
        })
    feature_importance.sort(
        key=lambda item: item["absolute_coefficient"],
        reverse=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(gpa_model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    IMPORTANCE_PATH.write_text(
        json.dumps(feature_importance, indent=2) + "\n", encoding="utf-8"
    )
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.write_text(create_seed_sql(metrics), encoding="utf-8")

    print(f"Model regresi GPA: {MODEL_PATH}")
    print(f"Metrik evaluasi test.csv: {METRICS_PATH}")
    print(f"Koefisien fitur: {IMPORTANCE_PATH}")
    print(f"Seed SQL siap ditinjau, tidak dijalankan: {SEED_PATH}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
