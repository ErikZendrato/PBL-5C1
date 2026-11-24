from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db import get_db
from ..deps import User, require
from ..services import ml

router = APIRouter(prefix="/admin", tags=["model"])
admin_only = require("admin")


@router.get("/models")
def list_models(user: User = Depends(admin_only)):
    return get_db().table("model_versions").select("*").order("id", desc=True).execute().data


@router.post("/models/train")
def train_model(user: User = Depends(admin_only)):
    try:
        return ml.train(user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/models/{mid}/activate")
def activate(mid: int, force: bool = False, user: User = Depends(admin_only)):
    db = get_db()
    rows = db.table("model_versions").select("*").eq("id", mid).execute().data
    if not rows:
        raise HTTPException(404, "Model tidak ditemukan")
    m = rows[0]
    if not force and m["baseline_mae"] is not None and float(m["mae"]) >= float(m["baseline_mae"]):
        raise HTTPException(400, "Model tidak lebih baik dari baseline (IP terakhir). "
                                 "Tambahkan data atau gunakan force=true jika tetap ingin memakai.")
    db.table("model_versions").update({"is_active": False}).eq("is_active", True).execute()
    db.table("model_versions").update({"is_active": True}).eq("id", mid).execute()
    return {"active": m["version"]}


class PredictBody(BaseModel):
    target_semester_id: int
    threshold: float | None = None


@router.post("/predict")
def run_prediction(body: PredictBody, user: User = Depends(admin_only)):
    try:
        return ml.predict_all(body.target_semester_id, body.threshold)
    except ValueError as e:
        raise HTTPException(400, str(e))
