from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from .db import get_db


class User(BaseModel):
    id: str
    role: str
    name: str


def current_user(authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Token tidak ada")
    token = authorization.split(" ", 1)[1]
    try:
        uid = get_db().auth.get_user(token).user.id
        rows = get_db().table("profiles").select("id,role,full_name,is_active").eq("id", uid).execute().data
    except Exception:
        raise HTTPException(401, "Token tidak valid")
    if not rows or not rows[0]["is_active"]:
        raise HTTPException(403, "Akun tidak aktif atau belum punya profil")
    p = rows[0]
    return User(id=p["id"], role=p["role"], name=p["full_name"])


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Tidak berwenang")
        return user

    return dep
