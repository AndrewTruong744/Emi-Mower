import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.exceptions import AuthenticationError
from src.services import auth
from src.services.temp_jwt import generate_jwt_token


async def test_verify_http_google_id_token_returns_verified_claims(monkeypatch):
    monkeypatch.setattr(
        auth.auth,
        "verify_id_token",
        lambda token, clock_skew_seconds: {"uid": "user-1"},
    )

    result = await auth.verify_http_google_id_token(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    )

    assert result == {"uid": "user-1"}


async def test_verify_http_google_id_token_maps_provider_failure(monkeypatch):
    def reject(*_args, **_kwargs):
        raise RuntimeError("bad token")

    monkeypatch.setattr(auth.auth, "verify_id_token", reject)
    with pytest.raises(AuthenticationError):
        await auth.verify_http_google_id_token(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        )


def test_generate_jwt_token_contains_subject():
    token = generate_jwt_token("user-1", exp_seconds=60)

    assert jwt.decode(token, options={"verify_signature": False})["sub"] == "user-1"
