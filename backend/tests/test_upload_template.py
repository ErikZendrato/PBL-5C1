import pandas as pd
import pytest

from backend.features import MODEL_FEATURES
from backend.make_upload_template import UPLOAD_COLUMNS, build_upload_template
from backend.main import validate_academic_csv


STUDENT_IDS = [
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
]


def feature_rows():
    return pd.DataFrame([
        {
            "age": 20,
            "admission_grade": 150,
            "previous_qualification_grade": 150,
            "gpa_semester_1": 3.2,
            "attendance_rate": 90,
            "assignments_submitted_rate": 95,
            "library_visits_per_month": 4,
            "lms_logins_per_week": 8,
            "weekly_work_hours": 5,
            "missed_deadlines": 1,
            "commute_time_mins": 30,
            "sleep_hours": 7,
            "course_type": "STEM",
            "study_mode": "Full-time",
        },
        {
            "age": 21,
            "admission_grade": 140,
            "previous_qualification_grade": 145,
            "gpa_semester_1": 3.4,
            "attendance_rate": 88,
            "assignments_submitted_rate": 92,
            "library_visits_per_month": 3,
            "lms_logins_per_week": 7,
            "weekly_work_hours": 4,
            "missed_deadlines": 0,
            "commute_time_mins": 25,
            "sleep_hours": 7.5,
            "course_type": "Business",
            "study_mode": "Online",
        },
    ], columns=MODEL_FEATURES)


def test_build_template_maps_ids_features_and_fallback_values():
    result = build_upload_template(
        feature_rows(),
        pd.DataFrame({"id": STUDENT_IDS}),
    )

    assert result.columns.tolist() == UPLOAD_COLUMNS
    assert result["student_id"].tolist() == STUDENT_IDS
    assert result["semester"].tolist() == [7, 7]
    assert result["ips"].tolist() == [3.2, 3.4]
    assert result["ipk"].tolist() == [3.2, 3.4]
    assert result["sks"].tolist() == [20, 20]
    assert result["kehadiran"].tolist() == [90, 88]
    assert result[MODEL_FEATURES].equals(feature_rows())
    validation = validate_academic_csv(result.to_csv(index=False).encode("utf-8"))
    assert validation["valid"]


def test_build_template_accepts_student_id_export_column():
    result = build_upload_template(
        feature_rows().iloc[:1],
        pd.DataFrame({"student_id": STUDENT_IDS[:1]}),
    )

    assert result.loc[0, "student_id"] == STUDENT_IDS[0]


def test_build_template_rejects_not_enough_unique_ids():
    with pytest.raises(ValueError, match="minimal 2 ID mahasiswa unik"):
        build_upload_template(feature_rows(), pd.DataFrame({"id": STUDENT_IDS[:1]}))


def test_build_template_rejects_invalid_student_uuid():
    with pytest.raises(ValueError, match="bukan UUID yang valid"):
        build_upload_template(feature_rows().iloc[:1], pd.DataFrame({"id": ["123"]}))


def test_build_template_rejects_missing_model_features():
    with pytest.raises(ValueError, match="Kolom fitur tidak ditemukan"):
        build_upload_template(
            feature_rows().drop(columns=["course_type"]),
            pd.DataFrame({"id": STUDENT_IDS}),
        )
