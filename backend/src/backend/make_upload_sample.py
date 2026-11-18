from pathlib import Path

import pandas as pd

from backend.features import MODEL_FEATURES


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
TEST_PATH = DATA_DIR / "test.csv"
UPLOAD_PATH = DATA_DIR / "upload_web.csv"
ANSWER_PATH = DATA_DIR / "kunci_jawaban.csv"
TARGET_COLUMN = "gpa_semester_2"
SAMPLE_SIZE = 50
RANDOM_STATE = 42


def build_sample(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required_columns = MODEL_FEATURES + [TARGET_COLUMN]
    missing_columns = sorted(set(required_columns) - set(data.columns))
    if missing_columns:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(missing_columns)}")
    if len(data) < SAMPLE_SIZE:
        raise ValueError(f"test.csv harus memiliki sedikitnya {SAMPLE_SIZE} baris.")

    sample = data.sample(n=SAMPLE_SIZE, random_state=RANDOM_STATE).reset_index(drop=True)
    if sample[required_columns].isna().any().any():
        raise ValueError("Sampel berisi fitur atau target kosong.")

    upload = sample[MODEL_FEATURES].copy()
    answer = pd.DataFrame({
        "sample_order": range(SAMPLE_SIZE),
        "nilai_asli": sample[TARGET_COLUMN].astype(float),
    })
    return upload, answer


def main() -> None:
    if not TEST_PATH.is_file():
        raise FileNotFoundError("test.csv tidak ditemukan. Jalankan split_data.py.")
    test_data = pd.read_csv(TEST_PATH)
    upload, answer = build_sample(test_data)
    upload.to_csv(UPLOAD_PATH, index=False)
    answer.to_csv(ANSWER_PATH, index=False)
    print(f"Sampel tanpa target: {UPLOAD_PATH} ({len(upload)} baris)")
    print(f"Kunci jawaban: {ANSWER_PATH} ({len(answer)} baris)")


if __name__ == "__main__":
    main()
