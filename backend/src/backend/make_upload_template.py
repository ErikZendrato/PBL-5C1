from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

import pandas as pd

from backend.features import MODEL_FEATURES


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DEFAULT_INPUT = DATA_DIR / "upload_web.csv"
DEFAULT_OUTPUT = DATA_DIR / "upload_template.csv"
UPLOAD_COLUMNS = [
    "student_id",
    "semester",
    "ips",
    "ipk",
    "sks",
    "kehadiran",
    *MODEL_FEATURES,
]
DEFAULT_SEMESTER = 7
DEFAULT_SKS = 20


def build_upload_template(
    features: pd.DataFrame,
    students: pd.DataFrame,
) -> pd.DataFrame:
    missing_features = [column for column in MODEL_FEATURES if column not in features.columns]
    if missing_features:
        raise ValueError(f"Kolom fitur tidak ditemukan: {', '.join(missing_features)}.")
    if features.empty:
        raise ValueError("CSV fitur tidak berisi baris data.")
    if features[MODEL_FEATURES].isna().any().any():
        raise ValueError("CSV fitur memiliki nilai kosong.")

    id_column = "id" if "id" in students.columns else "student_id" if "student_id" in students.columns else None
    if id_column is None:
        raise ValueError("CSV ekspor mahasiswa harus memiliki kolom id atau student_id.")

    raw_ids = students[id_column].astype("string").str.strip()
    if raw_ids.isna().any() or raw_ids.eq("").any():
        raise ValueError("CSV ekspor mahasiswa memiliki ID kosong.")

    student_ids: list[str] = []
    for row_number, raw_id in enumerate(raw_ids, start=2):
        try:
            student_ids.append(str(UUID(raw_id)))
        except ValueError as exc:
            raise ValueError(f"ID mahasiswa pada baris {row_number} bukan UUID yang valid.") from exc

    if len(set(student_ids)) != len(student_ids):
        raise ValueError("CSV ekspor mahasiswa memiliki ID berulang.")
    if len(student_ids) < len(features):
        raise ValueError(
            f"Dibutuhkan minimal {len(features)} ID mahasiswa unik untuk "
            f"{len(features)} baris pada semester {DEFAULT_SEMESTER}; "
            f"CSV hanya memiliki {len(student_ids)}."
        )

    result = features[MODEL_FEATURES].reset_index(drop=True).copy()
    result.insert(0, "student_id", student_ids[: len(result)])
    result.insert(1, "semester", DEFAULT_SEMESTER)
    result.insert(2, "ips", result["gpa_semester_1"])
    result.insert(3, "ipk", result["gpa_semester_1"])
    result.insert(4, "sks", DEFAULT_SKS)
    result.insert(5, "kehadiran", result["attendance_rate"])
    return result[UPLOAD_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gabungkan sampel fitur dengan ID mahasiswa untuk format upload web."
    )
    parser.add_argument(
        "--students",
        required=True,
        type=Path,
        help="CSV ekspor tabel students yang berisi kolom id atau student_id.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"CSV fitur tidak ditemukan: {args.input}")
    if not args.students.is_file():
        parser.error(f"CSV ekspor mahasiswa tidak ditemukan: {args.students}")

    try:
        features = pd.read_csv(args.input)
        students = pd.read_csv(args.students, dtype=str)
        upload = build_upload_template(features, students)
    except (OSError, pd.errors.ParserError, ValueError) as exc:
        parser.error(str(exc))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    upload.to_csv(args.output, index=False)
    print(f"CSV siap diunggah: {args.output} ({len(upload)} baris)")


if __name__ == "__main__":
    main()
