from fastapi.testclient import TestClient

from backend.auth import get_current_user, require_role
from backend.features import MODEL_FEATURES
from backend.main import ACADEMIC_COLUMNS, app, can_access_student, cors_origins, prediction_category, validate_academic_csv
from backend.model import get_top_factors


client = TestClient(app)
app.dependency_overrides[require_role("admin", "dosen", "mahasiswa")] = lambda: {"sub": "test-user", "role": "mahasiswa"}


STUDENT = {
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
}

CSV_ROW = {
    "student_id": "00000000-0000-4000-8000-000000000001",
    "semester": "1",
    "ips": "3.2",
    "ipk": "3.1",
    "sks": "20",
    "kehadiran": "90",
    "age": "20",
    "admission_grade": "150",
    "previous_qualification_grade": "150",
    "gpa_semester_1": "3.2",
    "attendance_rate": "90",
    "assignments_submitted_rate": "95",
    "library_visits_per_month": "4",
    "lms_logins_per_week": "8",
    "weekly_work_hours": "5",
    "missed_deadlines": "1",
    "commute_time_mins": "30",
    "sleep_hours": "7",
    "course_type": "STEM",
    "study_mode": "Full-time",
}


def csv_content(rows: list[dict[str, str]], columns: list[str] | None = None) -> bytes:
    columns = columns or ACADEMIC_COLUMNS
    content = [",".join(columns)]
    content.extend(",".join(row.get(column, "") for column in columns) for row in rows)
    return ("\n".join(content) + "\n").encode()


def test_predict():
    response = client.post("/predict", json=STUDENT)
    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["nilai_prediksi"] <= 4
    assert 0 <= result["batas_bawah"] <= result["nilai_prediksi"]
    assert result["nilai_prediksi"] <= result["batas_atas"] <= 4
    assert result["kategori"] in {"Baik", "Cukup", "Perlu Perhatian"}
    assert len(result["faktor"]) == 5
    assert "probabilitas" not in result


def test_predict_rejects_out_of_range_input():
    response = client.post("/predict", json={**STUDENT, "sleep_hours": 11})
    assert response.status_code == 422


def test_predict_rejects_unknown_category():
    response = client.post("/predict", json={**STUDENT, "course_type": "Reguler"})
    assert response.status_code == 422


def test_prediction_category_thresholds():
    assert prediction_category(3.25) == "Baik"
    assert prediction_category(2.5) == "Cukup"
    assert prediction_category(2.49) == "Perlu Perhatian"


def test_model_factors_include_standardized_coefficients():
    factors = get_top_factors()
    assert len(factors) == 5
    assert all(isinstance(factor["coefficient"], float) for factor in factors)


def test_cors_keeps_configured_origins_and_allows_local_vite_hosts(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://frontend.example,http://localhost:5173")

    assert cors_origins() == [
        "https://frontend.example",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_model_features_match_csv_template():
    assert set(MODEL_FEATURES).issubset(ACADEMIC_COLUMNS)


def test_admin_route_rejects_student_role(monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_user,
        lambda: {"sub": "student-1"},
    )
    monkeypatch.setattr("backend.auth.get_user_role", lambda _: "mahasiswa")

    response = client.get("/dashboard/admin")

    assert response.status_code == 403


def test_history_rejects_another_students_data(monkeypatch):
    monkeypatch.setattr(
        "backend.main.get_student",
        lambda _: {"id": "other-student", "profile_id": "someone-else", "dosen_wali_id": "lecturer-1"},
    )

    response = client.get("/students/00000000-0000-4000-8000-000000000002/history")

    assert response.status_code == 404


def test_student_and_lecturer_access_is_scoped_to_own_records():
    student = {"dosen_wali_id": "lecturer-1", "profile_id": "student-1"}

    assert can_access_student({"role": "admin", "sub": "admin-1"}, student)
    assert can_access_student({"role": "dosen", "sub": "lecturer-1"}, student)
    assert not can_access_student({"role": "dosen", "sub": "lecturer-2"}, student)
    assert can_access_student({"role": "mahasiswa", "sub": "student-1"}, student)
    assert not can_access_student({"role": "mahasiswa", "sub": "student-2"}, student)


def test_csv_missing_column():
    result = validate_academic_csv(b"student_id,semester,ips,ipk\nMHS-001,1,3,3")
    assert not result["valid"]
    assert any("Kolom wajib hilang" in error["pesan"] for error in result["errors"])


def test_csv_valid_features():
    result = validate_academic_csv(csv_content([CSV_ROW]))
    assert result["valid"]


def test_csv_feature_above_range():
    row = {**CSV_ROW, "attendance_rate": "120"}
    result = validate_academic_csv(csv_content([row]))
    assert not result["valid"]
    assert any("attendance_rate" in error["pesan"] for error in result["errors"])


def test_csv_unknown_category():
    row = {**CSV_ROW, "course_type": "Reguler"}
    result = validate_academic_csv(csv_content([row]))
    assert not result["valid"]
    assert any("course_type" in error["pesan"] for error in result["errors"])


def test_csv_empty_feature():
    row = {**CSV_ROW, "gpa_semester_1": ""}
    result = validate_academic_csv(csv_content([row]))
    assert not result["valid"]
    assert any("gpa_semester_1" in error["pesan"] for error in result["errors"])


def test_csv_duplicate():
    duplicate = {**CSV_ROW, "ips": "3.3"}
    result = validate_academic_csv(csv_content([CSV_ROW, duplicate]))
    assert not result["valid"]


def test_csv_empty_value():
    row = {**CSV_ROW, "student_id": "", "kehadiran": ""}
    result = validate_academic_csv(csv_content([row]))
    assert not result["valid"]


def test_csv_same_student_different_semesters_is_valid_duplicate_check():
    second_semester = {**CSV_ROW, "semester": "2"}
    result = validate_academic_csv(csv_content([CSV_ROW, second_semester]))
    assert not any("duplikat" in error["pesan"].lower() for error in result["errors"])
