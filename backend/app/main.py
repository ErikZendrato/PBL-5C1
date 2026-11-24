from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routers import admin, dosen, ml, views

app = FastAPI(title="API Sistem Prediksi Performa Akademik")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

for r in (views.router, admin.router, ml.router, dosen.router):
    app.include_router(r)

@app.get("/health")
def health():
    return {"status": "ok"}
