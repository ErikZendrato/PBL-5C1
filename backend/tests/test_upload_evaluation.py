import pandas as pd
import pytest

from backend.features import MODEL_FEATURES
from backend.evaluate_upload import evaluate
from backend.make_upload_sample import build_sample


def test_upload_sample_contains_features_but_not_target_or_id():
    data = pd.DataFrame({
        **{feature: [1] * 60 for feature in MODEL_FEATURES},
        "gpa_semester_2": [3.0] * 60,
        "person_id": range(60),
    })
    upload, answers = build_sample(data)

    assert len(upload) == 50
    assert list(upload.columns) == MODEL_FEATURES
    assert len(answers) == 50
    assert list(answers.columns) == ["sample_order", "nilai_asli"]


def test_evaluate_matches_by_sample_order():
    answers = pd.DataFrame({
        "sample_order": [0, 1, 2],
        "nilai_asli": [2.0, 3.0, 4.0],
    })
    predictions = pd.DataFrame({
        "sample_order": [2, 0, 1],
        "nilai_prediksi": [3.0, 1.0, 4.0],
    })

    assert evaluate(predictions, answers) == {"mae": 1.0, "rmse": 1.0}


def test_evaluate_rejects_mismatched_row_counts():
    answers = pd.DataFrame({"sample_order": [0], "nilai_asli": [2.0]})
    predictions = pd.DataFrame({"nilai_prediksi": [2.0, 3.0]})

    with pytest.raises(ValueError, match="Jumlah prediksi"):
        evaluate(predictions, answers)


def test_evaluate_rejects_missing_prediction_values():
    answers = pd.DataFrame({"sample_order": [0], "nilai_asli": [2.0]})
    predictions = pd.DataFrame({"nilai_prediksi": [None]})

    with pytest.raises(ValueError, match="harus berupa angka"):
        evaluate(predictions, answers)
