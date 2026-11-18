from __future__ import annotations

MODEL_FEATURES = [
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
    "course_type",
    "study_mode",
]

NUMERIC_FEATURE_RANGES = {
    "age": (15, 30),
    "admission_grade": (5.5, 200),
    "previous_qualification_grade": (30.2, 200),
    "gpa_semester_1": (0, 4),
    "attendance_rate": (0, 100),
    "assignments_submitted_rate": (0, 100),
    "library_visits_per_month": (0, 30),
    "lms_logins_per_week": (0, 29.6),
    "weekly_work_hours": (0, 40),
    "missed_deadlines": (0, 20),
    "commute_time_mins": (0, 120),
    "sleep_hours": (4, 10),
}
INTEGER_FEATURES = {
    "age",
    "library_visits_per_month",
    "missed_deadlines",
}
CATEGORY_OPTIONS = {
    "course_type": (
        "Arts & Humanities",
        "Business",
        "Health Sciences",
        "Law & Social Sciences",
        "STEM",
    ),
    "study_mode": ("Full-time", "Online", "Part-time"),
}


def prepare_model_features(data: dict) -> dict:
    missing = [name for name in MODEL_FEATURES if name not in data]
    if missing:
        raise ValueError(f"Kolom wajib belum lengkap: {', '.join(missing)}")
    return {name: data[name] for name in MODEL_FEATURES}
