import os
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from backend.database import get_user_role


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True, timeout=5)


def _decode_token(authorization: str) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token autentikasi tidak tersedia.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm == "ES256":
            supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
            if not supabase_url:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Konfigurasi autentikasi belum lengkap.",
                )
            issuer = f"{supabase_url}/auth/v1"
            signing_key = get_jwks_client(
                f"{issuer}/.well-known/jwks.json"
            ).get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
                issuer=issuer,
            )
        elif algorithm == "HS256":
            secret = os.getenv("SUPABASE_JWT_SECRET")
            if not secret:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Konfigurasi autentikasi belum lengkap.",
                )
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak valid atau sudah berakhir.",
            )
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak valid atau sudah berakhir.",
            )
        return payload
    except HTTPException:
        raise
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan verifikasi sesi Supabase tidak dapat dijangkau.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesi tidak valid atau sudah berakhir.") from exc


def get_current_user(authorization: str = Header(default=None)) -> dict:
    return _decode_token(authorization)


@lru_cache(maxsize=None)
def require_role(*roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        role = get_user_role(user["sub"])
        if role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Anda tidak memiliki akses untuk tindakan ini.")
        return {**user, "role": role}

    return dependency
