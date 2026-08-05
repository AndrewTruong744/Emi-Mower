import os

from dotenv import load_dotenv

# Load env file if it exists at root
load_dotenv()


class Settings:
    # Postgres configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        # e.g., postgresql+asyncpg://user:pass@host:port/db
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        # e.g., postgresql://user:pass@host:port/db
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Valkey configuration
    VALKEY_HOST: str = os.getenv("VALKEY_HOST", "localhost")
    VALKEY_PORT: int = int(os.getenv("VALKEY_PORT", "6379"))
    VALKEY_DB: int = int(os.getenv("VALKEY_DB", "0"))
    VALKEY_PASSWORD: str | None = os.getenv("VALKEY_PASSWORD", None)

    @property
    def VALKEY_URL(self) -> str:
        password_part = f":{self.VALKEY_PASSWORD}@" if self.VALKEY_PASSWORD else ""
        return f"redis://{password_part}{self.VALKEY_HOST}:{self.VALKEY_PORT}/{self.VALKEY_DB}"

    # Zenoh configuration
    ZENOH_APP_REST_URL: str = os.getenv(
        "ZENOH_APP_REST_URL", "http://127.0.0.1:8001"
    )
    ZENOH_MTLS_REST_URL: str = os.getenv(
        "ZENOH_MTLS_REST_URL", "http://127.0.0.1:8002"
    )
    ZENOH_CA_CERT: str = os.getenv("ZENOH_CA_CERT", "certs/ca/ca.crt")
    ZENOH_FASTAPI_CERT: str = os.getenv(
        "ZENOH_FASTAPI_CERT", "certs/fastapi/server.crt"
    )
    ZENOH_FASTAPI_KEY: str = os.getenv(
        "ZENOH_FASTAPI_KEY", "certs/fastapi/server.key"
    )

    # Cloudflare configuration
    CLOUDFLARE_ACCOUNT_ID: str = os.getenv("CLOUDFLARE_ACCOUNT_ID", "your_account_id")
    CLOUDFLARE_API_TOKEN: str = os.getenv("CLOUDFLARE_API_TOKEN", "your_api_token")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "default_jwt_secret_key_change_me")

    # LiveKit configuration
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

    @property
    def CF_API_URL(self) -> str:
        return os.getenv(
            "CF_API_URL",
            f"https://api.cloudflare.com/client/v4/accounts/{self.CLOUDFLARE_ACCOUNT_ID}/calls/apps",
        )

    @property
    def CF_RTC_URL(self) -> str:
        return f"https://rtc.live.cloudflare.com/v1/apps/{self.CLOUDFLARE_ACCOUNT_ID}"


settings = Settings()
