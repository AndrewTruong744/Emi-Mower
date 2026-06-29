import logging
from contextlib import asynccontextmanager

import valkey.asyncio as valkey
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import String, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base, engine, get_db
from src.config.mqtt import start_mqtt, stop_mqtt
from src.config.socketio import sio_app
from src.config.valkey_client import close_valkey_pool, get_valkey
from backend.src.api.protected.protected import router as auth_router
from backend.src.api.public.public import router as public_router
from src.services.auth import verify_gcp_identity
from src.services.firebase_init import initialize_backend_auth

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
    # Startup: Initialize Firebase Admin SDK
    initialize_backend_auth()

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
        from src.config.valkey_client import get_valkey_client

        v_client = get_valkey_client()
        await v_client.ping()
        await v_client.close()
        logger.info("Valkey connection verified successfully.")
    except Exception as e:
        logger.error(f"Valkey connection failed: {e}")

    # Startup: Start MQTT client
    logger.info("Starting MQTT client...")
    await start_mqtt()

    yield

    # Shutdown: Clean up connections
    logger.info("Stopping MQTT client...")
    await stop_mqtt()

    logger.info("Closing Valkey connection pool...")
    await close_valkey_pool()
    logger.info("Valkey connection pool closed.")


app = FastAPI(
    title="Emi Mower Backend",
    description="FastAPI with PostgreSQL, SQLAlchemy, and Valkey integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(verify_gcp_identity)],  # ◄── FORCES SECURITY ON ALL CHILDS
)
app.include_router(public_router, prefix="/public", tags=["public"])

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
