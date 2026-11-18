from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DEFAULT_PREDICTIONS_PATH = DATA_DIR / "prediksi_web.csv"
ANSWER_PATH = DATA_DIR / "kunci_jawaban.csv"


def read_predictions(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("predictions")
        if not isinstance(payload, list):
            raise ValueError(
                "JSON prediksi harus berupa daftar hasil atau respons /predict/batch."
            )
        values = [
            item.get("nilai_prediksi") if isinstance(item, dict) else item
            for item in payload
        ]
        return pd.DataFrame({"nilai_prediksi": values})

    predictions = pd.read_csv(path)
    if "nilai_prediksi" not in predictions.columns:
        raise ValueError("File prediksi harus memiliki kolom nilai_prediksi.")
    return predictions


def evaluate(predictions: pd.DataFrame, answers: pd.DataFrame) -> dict[str, float]:
    required_answer_columns = {"sample_order", "nilai_asli"}
    missing = required_answer_columns - set(answers.columns)
    if missing:
        raise ValueError(f"Kolom kunci jawaban tidak ditemukan: {', '.join(sorted(missing))}")
    if "nilai_prediksi" not in predictions.columns:
        raise ValueError("Kolom nilai_prediksi wajib ada pada hasil prediksi.")
    if len(predictions) != len(answers):
        raise ValueError(
            f"Jumlah prediksi ({len(predictions)}) harus sama dengan "
            f"jumlah kunci ({len(answers)})."
        )

    if "sample_order" in predictions.columns:
        if predictions["sample_order"].duplicated().any():
            raise ValueError("sample_order pada hasil prediksi harus unik.")
        merged = answers.merge(
            predictions[["sample_order", "nilai_prediksi"]],
            on="sample_order",
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        if not merged["_merge"].eq("both").all():
            raise ValueError("sample_order hasil prediksi tidak cocok dengan kunci.")
        actual = merged["nilai_asli"]
        predicted = merged["nilai_prediksi"]
    else:
        actual = answers["nilai_asli"]
        predicted = predictions["nilai_prediksi"]

    actual_values = pd.to_numeric(actual, errors="coerce")
    predicted_values = pd.to_numeric(predicted, errors="coerce")
    if actual_values.isna().any() or predicted_values.isna().any():
        raise ValueError("Nilai target dan prediksi harus berupa angka yang terisi.")

    return {
        "mae": float(mean_absolute_error(actual_values, predicted_values)),
        "rmse": float(mean_squared_error(actual_values, predicted_values) ** 0.5),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hitung MAE dan RMSE hasil prediksi web."
    )
    parser.add_argument(
        "predictions",
        nargs="?",
        type=Path,
        default=DEFAULT_PREDICTIONS_PATH,
        help="CSV/JSON ekspor hasil /predict/batch (kolom nilai_prediksi).",
    )
    parser.add_argument(
        "--answers",
        type=Path,
        default=ANSWER_PATH,
        help="CSV kunci jawaban dari make_upload_sample.py.",
    )
    args = parser.parse_args()
    if not args.predictions.is_file():
        raise FileNotFoundError(
            f"File hasil prediksi tidak ditemukan: {args.predictions}"
        )
    if not args.answers.is_file():
        raise FileNotFoundError(
            f"Kunci jawaban tidak ditemukan: {args.answers}. "
            "Jalankan make_upload_sample.py."
        )

    metrics = evaluate(read_predictions(args.predictions), pd.read_csv(args.answers))
    print(f"Jumlah sampel: {len(pd.read_csv(args.answers))}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")


if __name__ == "__main__":
    main()
