from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "student_performance.csv"
TRAIN_PATH = BASE_DIR / "data" / "train.csv"
TEST_PATH = BASE_DIR / "data" / "test.csv"
TEST_SIZE = 0.15
RANDOM_STATE = 42


def find_id_column(data: pd.DataFrame) -> str | None:
    id_columns = [
        column
        for column in data.columns
        if column.lower() == "id" or column.lower().endswith("_id")
    ]
    return next(
        (column for column in id_columns if data[column].duplicated().any()),
        None,
    )


def main() -> None:
    data = pd.read_csv(DATA_PATH)
    id_column = find_id_column(data)
    if id_column:
        if data[id_column].isna().any():
            raise ValueError(
                f"Kolom ID {id_column} berisi nilai kosong; "
                "pemisahan grup tidak aman."
            )
        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
        )
        train_indices, test_indices = next(
            splitter.split(data, groups=data[id_column])
        )
        train_data = data.iloc[train_indices]
        test_data = data.iloc[test_indices]
        split_method = f"GroupShuffleSplit ({id_column})"
    else:
        train_data, test_data = train_test_split(
            data,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
        )
        split_method = "train_test_split (tanpa stratifikasi)"

    train_data.to_csv(TRAIN_PATH, index=False)
    test_data.to_csv(TEST_PATH, index=False)

    print(f"Metode pemisahan: {split_method}")
    print(f"Data latih: {len(train_data)} baris -> {TRAIN_PATH}")
    print(f"Data uji: {len(test_data)} baris -> {TEST_PATH}")


if __name__ == "__main__":
    main()
