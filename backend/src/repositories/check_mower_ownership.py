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

logger = logging.getLogger("repositories.check_mower_ownership")


async def check_mower_ownership(mower_id: str, db: AsyncSession) -> str | None:
    """
    Checks Valkey for key 'mower:{mower_id}:owner'.
    If cache hit, refreshes TTL to 24hr and returns owner user_id or None.
    If cache miss, queries Postgres via provided AsyncSession and caches in Valkey.
    Returns owner user_id (str) or None. Raises RepositoryError on DB error.
    """
    mower_uuid_str = str(mower_id).strip().lower()
    valkey_key = mower_owner_key(mower_uuid_str)

    try:
        async with get_valkey_client() as v_client:
            cached = await v_client.get(valkey_key)
            if cached is not None:
                logger.info(f"Valkey hit for mower owner: {valkey_key}")
                await v_client.expire(valkey_key, VALKEY_CACHE_TTL_SECONDS)
                if cached in ("dne", "none", ""):
                    return None
                return cached
    except Exception as valkey_err:
        logger.error(f"Valkey error during ownership lookup: {valkey_err}")

    try:
        m_uuid = uuid.UUID(mower_uuid_str)
    except ValueError as val_err:
        logger.error(f"Invalid UUID format '{mower_uuid_str}': {val_err}")
        return None

    # Cache miss: query Postgres
    logger.info(f"Valkey cache miss for key {valkey_key}. Checking PostgreSQL...")
    owner_id = None
    try:
        stmt = select(MowerModel.owner_id).where(MowerModel.id == m_uuid)
        result = await db.execute(stmt)
        row = result.fetchone()

        if not row:
            owner_id = None
        else:
            owner_id = row[0]
    except Exception as db_err:
        logger.error(
            f"Database query failed in check_mower_ownership: {db_err}",
            exc_info=True,
        )
        raise RepositoryError(
            f"Database lookup failed for mower '{mower_id}'"
        ) from db_err

    # Cache results in Valkey
    try:
        async with get_valkey_client() as v_client:
            cache_value = MowerOwnerCache(
                owner_id if owner_id is not None else "dne"
            ).root
            await v_client.setex(valkey_key, VALKEY_CACHE_TTL_SECONDS, cache_value)
            logger.info(f"Cached ownership '{cache_value}' under key: {valkey_key}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache ownership in Valkey: {valkey_err}")

    return owner_id
