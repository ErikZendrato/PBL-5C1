from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from backend import auth


def token_payload() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": "00000000-0000-4000-8000-000000000001",
        "aud": "authenticated",
        "iss": "https://project.supabase.co/auth/v1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }


def test_decode_token_accepts_supabase_es256_jwks(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    token = jwt.encode(
        token_payload(),
        private_key,
        algorithm="ES256",
        headers={"kid": "test-key"},
    )
    client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=public_key)
    )
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(auth, "get_jwks_client", lambda _: client)

    assert auth._decode_token(f"Bearer {token}")["sub"] == token_payload()["sub"]


def test_decode_token_rejects_es256_token_with_wrong_issuer(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    payload = token_payload()
    payload["iss"] = "https://other-project.supabase.co/auth/v1"
    token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "test-key"})
    client = SimpleNamespace(
        get_signing_key_from_jwt=lambda _: SimpleNamespace(key=private_key.public_key())
    )
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(auth, "get_jwks_client", lambda _: client)

    with pytest.raises(HTTPException) as error:
        auth._decode_token(f"Bearer {token}")

    assert error.value.status_code == 401


def test_decode_token_keeps_legacy_hs256_support(monkeypatch):
    secret = "local-test-secret-that-is-not-a-production-credential"
    token = jwt.encode(token_payload(), secret, algorithm="HS256")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)

    assert auth._decode_token(f"Bearer {token}")["sub"] == token_payload()["sub"]


def test_decode_token_rejects_unconfigured_algorithm(monkeypatch):
    secret = "local-test-secret-that-is-long-enough-for-hmac-sha512-validation"
    token = jwt.encode(token_payload(), secret, algorithm="HS512")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", secret)

    with pytest.raises(HTTPException) as error:
        auth._decode_token(f"Bearer {token}")

    assert error.value.status_code == 401
