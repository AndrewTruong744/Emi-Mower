import jwt

from src.config.settings import settings
from src.services.temp_jwt import generate_jwt_token


def test_generate_jwt_token_contains_subject(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-jwt-secret-" + "x" * 32)
    token = generate_jwt_token("user-1", exp_seconds=60)

    assert jwt.decode(token, options={"verify_signature": False})["sub"] == "user-1"
