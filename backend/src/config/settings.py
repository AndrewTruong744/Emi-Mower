"""Authoritative environment configuration for backend processes and tools."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class SettingsValidationError(RuntimeError):
    """Raised when a backend process lacks required runtime configuration."""


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


class Settings:
    """The sole environment-variable boundary for backend code."""

    POSTGRES_USER: str = os.getenv("POSTGRES_USER") or "postgres"
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD") or "postgres"
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST") or "localhost"
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT") or "5432"
    POSTGRES_DB: str = os.getenv("POSTGRES_DB") or "postgres"

    VALKEY_HOST: str = os.getenv("VALKEY_HOST") or "localhost"
    VALKEY_PORT: int = int(os.getenv("VALKEY_PORT") or "6379")
    VALKEY_PASSWORD: str | None = os.getenv("VALKEY_PASSWORD") or None

    ZENOH_APP_REST_URL: str = os.getenv("ZENOH_APP_REST_URL") or "http://127.0.0.1:8001"
    ZENOH_MTLS_ENDPOINT: str = os.getenv("ZENOH_MTLS_ENDPOINT") or "tls/127.0.0.1:7448"
    ZENOH_MTLS_REST_URL: str = (
        os.getenv("ZENOH_MTLS_REST_URL") or "http://127.0.0.1:8002"
    )
    ZENOH_BOOTSTRAP_ENDPOINT: str = (
        os.getenv("ZENOH_BOOTSTRAP_ENDPOINT") or "tls/127.0.0.1:7449"
    )
    ZENOH_BOOTSTRAP_VERIFY_NAME: bool = _env_bool("ZENOH_BOOTSTRAP_VERIFY_NAME", True)
    ZENOH_CA_CERT: str = (
        os.getenv("ZENOH_CA_CERT") or "/run/emi-mower/identity/root_ca.pem"
    )
    ZENOH_FASTAPI_CERT: str = (
        os.getenv("ZENOH_FASTAPI_CERT")
        or "/run/emi-mower/identity/current/fastapi.crt"
    )
    ZENOH_FASTAPI_KEY: str = (
        os.getenv("ZENOH_FASTAPI_KEY")
        or "/run/emi-mower/identity/current/fastapi.key"
    )
    STEP_CA_URL: str = os.getenv("STEP_CA_URL") or "https://localhost:9000"
    STEP_CA_PROVISIONER_PASSWORD_FILE: str = (
        os.getenv("STEP_CA_PROVISIONER_PASSWORD_FILE")
        or "/run/emi-mower/issuer/provisioner-password"
    )
    JWT_SECRET: str = os.getenv("JWT_SECRET") or ""

    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL") or ""
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY") or ""
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET") or ""

    GCP_PROJECT_ID: str = (
        os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "emi-mower"
    )
    GCS_CUTOUT_BUCKET: str = (
        os.getenv("GCS_CUTOUT_BUCKET") or "emi-mower-cutouts-sandbox"
    )
    GCS_UPLOAD_URL_TTL_SECONDS: int = int(
        os.getenv("GCS_UPLOAD_URL_TTL_SECONDS") or "900"
    )
    GCS_DOWNLOAD_URL_TTL_SECONDS: int = int(
        os.getenv("GCS_DOWNLOAD_URL_TTL_SECONDS") or "900"
    )

    FIREBASE_DISABLED: bool = _env_bool("FIREBASE_DISABLED", False)
    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = (
        os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or None
    )

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def validate_startup(self) -> None:
        """Fail early for configuration that must never receive a fallback."""
        missing: list[str] = []
        if not self.JWT_SECRET:
            missing.append("JWT_SECRET")

        livekit_values = (
            self.LIVEKIT_URL,
            self.LIVEKIT_API_KEY,
            self.LIVEKIT_API_SECRET,
        )
        if any(livekit_values) and not all(livekit_values):
            missing.extend(
                name
                for name, configured in zip(
                    ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"),
                    livekit_values,
                    strict=True,
                )
                if not configured
            )

        if missing:
            raise SettingsValidationError(
                "Missing required configuration: " + ", ".join(missing)
            )


settings = Settings()
