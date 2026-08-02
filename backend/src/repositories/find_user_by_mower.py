import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel
from src.schemas.valkey import (
    VALKEY_CACHE_TTL_SECONDS,
    MowerOwnerCache,
    mower_owner_key,
)

logger = logging.getLogger("repositories.find_user_by_mower")


async def find_user_by_mower(mower_id: str | uuid.UUID, db: AsyncSession) -> str | None:
    """
    Checks Valkey for key 'mower:{mower_id}:owner'.
    If cache hit, refreshes TTL to 24hr and returns owner_id or None.
    If cache miss, queries Postgres via AsyncSession and caches in Valkey.
    Returns owner_id or None. Raises RepositoryError on DB failure.
    """
    mower_uuid_str = str(mower_id).strip().lower()
    valkey_key = mower_owner_key(mower_uuid_str)

    try:
        # 1. Check Valkey cache
        async with get_valkey_client() as v_client:
            cached_owner = await v_client.get(valkey_key)
            if cached_owner is not None:
                logger.info(f"Valkey cache hit for mower owner key: {valkey_key}")
                await v_client.expire(valkey_key, VALKEY_CACHE_TTL_SECONDS)
                if cached_owner in ("dne", "none", ""):
                    return None
                return cached_owner
    except Exception as valkey_err:
        logger.error(f"Valkey error during mower owner check: {valkey_err}")

    # Convert mower_id to UUID object for SQLAlchemy query
    try:
        m_uuid = uuid.UUID(mower_uuid_str) if isinstance(mower_id, str) else mower_id
    except ValueError as val_err:
        logger.error(f"Invalid UUID format '{mower_uuid_str}': {val_err}")
        return None

    # 2. Cache miss: check PostgreSQL
    logger.info(f"Valkey cache miss for key {valkey_key}. Checking PostgreSQL...")
    owner_id_result = None
    try:
        stmt = select(MowerModel.owner_id).where(MowerModel.id == m_uuid)
        result = await db.execute(stmt)
        row = result.fetchone()

        if row and row[0] is not None:
            owner_id_result = row[0]
    except Exception as db_err:
        logger.error(
            "Database lookup failed for mower %s: %s",
            mower_uuid_str,
            db_err,
            exc_info=True,
        )
        raise RepositoryError(
            f"Database lookup failed for mower '{mower_uuid_str}'"
        ) from db_err

    # 3. Populate Valkey cache with 24hr expiration
    try:
        async with get_valkey_client() as v_client:
            cache_val = MowerOwnerCache(
                owner_id_result if owner_id_result is not None else "dne"
            ).root
            await v_client.setex(valkey_key, VALKEY_CACHE_TTL_SECONDS, cache_val)
            logger.info(f"Cached owner '{cache_val}' under key: {valkey_key}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache owner result in Valkey: {valkey_err}")

    return owner_id_result
