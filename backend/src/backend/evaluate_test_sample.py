from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from backend.features import MODEL_FEATURES


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
TRAIN_PATH = DATA_DIR / "train.csv"
TEST_PATH = DATA_DIR / "test.csv"
MODEL_PATH = BASE_DIR / "models" / "linear_regression_v2_1" / "model.pkl"
ANSWER_PATH = DATA_DIR / "kunci_jawaban.csv"
RESULT_PATH = DATA_DIR / "hasil_prediksi_test.csv"
UPLOAD_FEATURES_PATH = DATA_DIR / "upload_test_features.csv"
TARGET = "gpa_semester_2"
SAMPLE_SIZE = 30
RANDOM_STATE = 42


def calculate_metrics(actual: pd.Series, predicted) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)),
    }


def main() -> None:
    missing_files = [
        path for path in (TEST_PATH, MODEL_PATH)
        if not path.is_file()
    ]
    if missing_files:
        raise FileNotFoundError(
            "File yang dibutuhkan tidak ditemukan: "
            + ", ".join(str(path) for path in missing_files)
        )

    test_data = pd.read_csv(TEST_PATH)
    required = [*MODEL_FEATURES, TARGET]
    missing_columns = sorted(set(required) - set(test_data.columns))
    if missing_columns:
        raise ValueError(f"Kolom wajib tidak ada di test.csv: {', '.join(missing_columns)}")
    if test_data[required].isna().any().any():
        raise ValueError("test.csv memiliki fitur atau target kosong.")
    if len(test_data) < SAMPLE_SIZE:
        raise ValueError(f"test.csv harus memiliki sedikitnya {SAMPLE_SIZE} baris.")

    if TRAIN_PATH.is_file():
        train_data = pd.read_csv(TRAIN_PATH, usecols=["person_id"])
        if "person_id" in test_data.columns:
            overlap = set(train_data["person_id"]) & set(test_data["person_id"])
            if overlap:
                raise ValueError(
                    f"train.csv dan test.csv memiliki {len(overlap)} person_id yang sama."
                )

    model = joblib.load(MODEL_PATH)
    sample = test_data.sample(n=SAMPLE_SIZE, random_state=RANDOM_STATE).reset_index(drop=True)
    sample_predictions = model.predict(sample[MODEL_FEATURES])
    all_test_predictions = model.predict(test_data[MODEL_FEATURES])

    actual_sample = sample[TARGET].astype(float)
    answer = pd.DataFrame({
        "sample_order": range(1, SAMPLE_SIZE + 1),
        **({"person_id": sample["person_id"]} if "person_id" in sample.columns else {}),
        "nilai_asli": actual_sample,
    })
    differences = sample_predictions - actual_sample.to_numpy()
    results = pd.DataFrame({
        "sample_order": range(1, SAMPLE_SIZE + 1),
        **({"person_id": sample["person_id"]} if "person_id" in sample.columns else {}),
        "nilai_asli": actual_sample,
        "nilai_prediksi": sample_predictions,
        "selisih": differences,
        "selisih_absolut": abs(differences),
    })
    answer.to_csv(ANSWER_PATH, index=False)
    results.to_csv(RESULT_PATH, index=False)
    sample[MODEL_FEATURES].to_csv(UPLOAD_FEATURES_PATH, index=False)

    sample_metrics = calculate_metrics(actual_sample, sample_predictions)
    full_metrics = calculate_metrics(
        test_data[TARGET].astype(float),
        all_test_predictions,
    )
    print(f"Split data: test.csv ({len(test_data)} baris), train-test ID overlap: 0")
    print(f"Sampel: {SAMPLE_SIZE} baris acak, random_state={RANDOM_STATE}")
    print(f"Kunci jawaban: {ANSWER_PATH}")
    print(f"Hasil prediksi: {RESULT_PATH}")
    print(f"Fitur untuk CSV upload (menunggu ID mahasiswa): {UPLOAD_FEATURES_PATH}")
    print("Metrik 30 sampel: " + json.dumps(sample_metrics, sort_keys=True))
    print("Metrik seluruh test.csv: " + json.dumps(full_metrics, sort_keys=True))
    print("\nRingkasan 5 baris:")
    print(results.head(5).to_string(index=False, float_format=lambda value: f"{value:.4f}"))


if __name__ == "__main__":
    main()
