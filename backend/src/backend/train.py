
from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, LogisticRegression

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)


# ==========================================
# 1. LOKASI FILE
# ==========================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_PATH = BASE_DIR / "data" / "student_performance.csv"
MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2. MEMBACA DATASET
# ==========================================

data = pd.read_csv(DATA_PATH)

print("Jumlah data:", data.shape)


# ==========================================
# 3. MENENTUKAN FITUR
# ==========================================

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


# ==========================================
# 4. PREPROCESSING
# ==========================================

def create_preprocessor():
    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                StandardScaler(),
                numeric_features,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features,
            ),
        ]
    )


# ==========================================
# 5. MODEL PREDIKSI GPA
# ==========================================

print("\n===== TRAINING MODEL GPA =====")

X_gpa = data[features]
y_gpa = data["gpa_semester_2"]

X_train, X_test, y_train, y_test = train_test_split(
    X_gpa,
    y_gpa,
    test_size=0.2,
    random_state=42,
)

gpa_model = Pipeline(
    steps=[
        ("preprocessing", create_preprocessor()),
        ("model", LinearRegression()),
    ]
)

gpa_model.fit(X_train, y_train)

gpa_predictions = gpa_model.predict(X_test)

mae = mean_absolute_error(y_test, gpa_predictions)
rmse = mean_squared_error(y_test, gpa_predictions) ** 0.5
r2 = r2_score(y_test, gpa_predictions)

print("MAE:", round(mae, 4))
print("RMSE:", round(rmse, 4))
print("R2 Score:", round(r2, 4))

joblib.dump(gpa_model, MODEL_DIR / "gpa_model.pkl")


# ==========================================
# 6. MODEL PREDIKSI DROPOUT
# ==========================================

print("\n===== TRAINING MODEL DROPOUT =====")

X_dropout = data[features]
y_dropout = data["dropout"]

X_train, X_test, y_train, y_test = train_test_split(
    X_dropout,
    y_dropout,
    test_size=0.2,
    random_state=42,
    stratify=y_dropout,
)

dropout_model = Pipeline(
    steps=[
        ("preprocessing", create_preprocessor()),
        (
            "model",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ]
)

dropout_model.fit(X_train, y_train)

dropout_predictions = dropout_model.predict(X_test)
dropout_probabilities = dropout_model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, dropout_predictions)
precision = precision_score(
    y_test, dropout_predictions, zero_division=0
)
recall = recall_score(
    y_test, dropout_predictions, zero_division=0
)
f1 = f1_score(
    y_test, dropout_predictions, zero_division=0
)
roc_auc = roc_auc_score(y_test, dropout_probabilities)

print("Accuracy:", round(accuracy, 4))
print("Precision:", round(precision, 4))
print("Recall:", round(recall, 4))
print("F1 Score:", round(f1, 4))
print("ROC AUC:", round(roc_auc, 4))

print("\nClassification Report:")
print(classification_report(y_test, dropout_predictions))

print("Confusion Matrix:")
print(confusion_matrix(y_test, dropout_predictions))

joblib.dump(
    dropout_model,
    MODEL_DIR / "dropout_model.pkl",
)


# ==========================================
# 7. MENYIMPAN METRIK EVALUASI
# ==========================================

metrics = {
    "gpa_model": {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2_score": float(r2),
    },
    "dropout_model": {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
    },
}

with open(MODEL_DIR / "metrics.json", "w") as file:
    json.dump(metrics, file, indent=4)

print("\n===== SELESAI =====")
print("Model berhasil disimpan di folder models/")
