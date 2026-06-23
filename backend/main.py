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
    lifespan=lifespan
)

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
    valkey_client: valkey.Valkey = Depends(get_valkey)
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
                "valkey": valkey_status
            }
        )

    return {
        "status": "healthy",
        "postgres": postgres_status,
        "valkey": valkey_status
    }

@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: ItemCreate,
    db: AsyncSession = Depends(get_db),
    valkey_client: valkey.Valkey = Depends(get_valkey)
) -> Any:
    """
    Creates an item in Postgres and caches its name in Valkey for 60 seconds.
    """
    new_item = Item(name=item_in.name, description=item_in.description)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    # Cache the item name in Valkey
    try:
        cache_key = f"item:{new_item.id}"
        await valkey_client.setex(cache_key, 60, new_item.name)
        logger.info(f"Cached item name in Valkey with key: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache item in Valkey: {e}")

    return new_item

@app.get("/items/{item_id}")
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    valkey_client: valkey.Valkey = Depends(get_valkey)
) -> dict[str, Any]:
    """
    Retrieves an item. Checks Valkey cache first (cache hit).
    If cache miss, queries Postgres, writes to Valkey cache, and returns.
    """
    cache_key = f"item:{item_id}"
    
    # Try reading from Valkey cache
    try:
        cached_name = await valkey_client.get(cache_key)
        if cached_name:
            logger.info(f"Cache hit for item {item_id}")
            return {
                "id": item_id,
                "name": cached_name,
                "source": "valkey_cache"
            }
    except Exception as e:
        logger.warning(f"Valkey cache read error: {e}")

    # Cache miss: Query Postgres
    logger.info(f"Cache miss for item {item_id}. Querying database...")
    query = select(Item).where(Item.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    # Write back to cache for subsequent requests (expire in 60s)
    try:
        await valkey_client.setex(cache_key, 60, item.name)
    except Exception as e:
        logger.warning(f"Valkey write-back error: {e}")

    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "source": "postgresql_db"
    }
