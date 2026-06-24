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


settings = Settings()
