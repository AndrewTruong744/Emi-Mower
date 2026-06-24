from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import String, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column
import valkey.asyncio as valkey

from config.database import engine, Base, get_db
from config.settings import settings
from config.valkey_client import get_valkey, close_valkey_pool
from config.socketio import sio_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")


# Define a simple demonstration model to verify SQLAlchemy connectivity
class Item(Base):
    __tablename__ = "demo_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)


# Lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables
    logger.info("Initializing database tables (if they don't exist)...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # Startup: Verify Valkey connection
    logger.info("Testing Valkey connection...")
    try:
        from config.valkey_client import get_valkey_client

        v_client = get_valkey_client()
        await v_client.ping()
        await v_client.close()
        logger.info("Valkey connection verified successfully.")
    except Exception as e:
        logger.error(f"Valkey connection failed: {e}")

    yield

    # Shutdown: Clean up connections
    logger.info("Closing Valkey connection pool...")
    await close_valkey_pool()
    logger.info("Valkey connection pool closed.")


app = FastAPI(
    title="Emi Mower Backend",
    description="FastAPI with PostgreSQL, SQLAlchemy, and Valkey integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount Socket.IO ASGI application under /ws
# The client can connect to: http://<host>:<port>/ws/socket.io
app.mount("/ws", sio_app)


# Pydantic schemas for endpoint data validation
class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    valkey_client: valkey.Valkey = Depends(get_valkey),
) -> dict[str, str]:
    """
    Health check endpoint that verifies connectivity to Postgres and Valkey.
    """
    postgres_status = "unhealthy"
    valkey_status = "unhealthy"

    # Test Postgres
    try:
        await db.execute(text("SELECT 1"))
        postgres_status = "healthy"
    except Exception as e:
        logger.error(f"Postgres health check failed: {e}")

    # Test Valkey
    try:
        await valkey_client.ping()
        valkey_status = "healthy"
    except Exception as e:
        logger.error(f"Valkey health check failed: {e}")

    if postgres_status != "healthy" or valkey_status != "healthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "postgres": postgres_status,
                "valkey": valkey_status,
            },
        )

    return {"status": "healthy", "postgres": postgres_status, "valkey": valkey_status}
