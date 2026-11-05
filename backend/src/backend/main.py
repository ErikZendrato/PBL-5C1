from backend.database import save_prediction, get_predictions
from fastapi import HTTPException
from fastapi import FastAPI,HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.model import predict_gpa, predict_dropout


app = FastAPI(
    title="Prediksi Performa Mahasiswa API",
    description="API untuk prediksi GPA dan risiko dropout mahasiswa.",
    version="1.0.0",
)


# Mengizinkan frontend React mengakses backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Struktur data input mahasiswa
class StudentFeatures(BaseModel):
    age: int = Field(ge=0)
    admission_grade: float
    previous_qualification_grade: float
    gpa_semester_1: float = Field(ge=0, le=4)
    attendance_rate: float = Field(ge=0, le=100)
    assignments_submitted_rate: float = Field(ge=0, le=100)
    library_visits_per_month: int = Field(ge=0)
    lms_logins_per_week: int = Field(ge=0)
    weekly_work_hours: float = Field(ge=0)
    missed_deadlines: int = Field(ge=0)
    commute_time_mins: float = Field(ge=0)
    sleep_hours: float = Field(ge=0)
    course_type: str
    study_mode: str


@app.get("/")
def home():
    return {
        "message": "API Prediksi Performa Mahasiswa aktif"
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}



@app.post("/predict/gpa")
def predict_gpa_endpoint(student: StudentFeatures):
    try:
        features = student.model_dump()

        result = predict_gpa(features)

        saved_data = save_prediction(
            prediction_type="GPA",
            input_features=features,
            predicted_value=result,
        )

        return {
            "prediction_type": "GPA",
            "predicted_gpa": result,
            "saved_to_database": True,
            "prediction_id": saved_data[0]["id"],
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Gagal memproses atau menyimpan prediksi GPA.",
        ) from error


@app.post("/predict/dropout")
def predict_dropout_endpoint(student: StudentFeatures):
    try:
        features = student.model_dump()

        result = predict_dropout(features)

        saved_data = save_prediction(
            prediction_type="DROPOUT",
            input_features=features,
            predicted_class=result["dropout_prediction"],
            dropout_probability=result["dropout_probability"],
        )

        return {
            "prediction_type": "Dropout",
            **result,
            "saved_to_database": True,
            "prediction_id": saved_data[0]["id"],
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Gagal memproses atau menyimpan prediksi dropout.",
        ) from error



@app.post("/predict/dropout")
def predict_dropout_endpoint(student: StudentFeatures):
    result = predict_dropout(student.model_dump())

    return {
        "prediction_type": "Dropout",
        **result,
    }


@app.get("/predictions")
def get_prediction_history(
    limit: int = Query(default=50, ge=1, le=100)
):
    try:
        predictions = get_predictions(limit)

        return {
            "total": len(predictions),
            "predictions": predictions,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Gagal mengambil riwayat prediksi.",
        ) from error
