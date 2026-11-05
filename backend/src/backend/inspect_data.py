
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "student_performance.csv"

# Membaca dataset
data = pd.read_csv(DATA_PATH)

print("\n===== INFORMASI DATASET =====")
print("Jumlah baris dan kolom:", data.shape)

print("\n===== NAMA KOLOM =====")
print(data.columns.tolist())

print("\n===== TIPE DATA =====")
print(data.dtypes)

print("\n===== DATA KOSONG =====")
print(data.isnull().sum())

print("\n===== DATA DUPLIKAT =====")
print(data.duplicated().sum())

print("\n===== DISTRIBUSI DROPOUT =====")
print(data["dropout"].value_counts(dropna=False))

print("\n===== DISTRIBUSI GPA SEMESTER 2 =====")
print(data["gpa_semester_2"].describe())

print("\n===== CONTOH DATA =====")
print(data.head())
