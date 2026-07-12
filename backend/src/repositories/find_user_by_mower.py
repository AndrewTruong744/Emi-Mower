import logging
import uuid

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.find_user_by_mower")


async def find_user_by_mower(mower_id: str | uuid.UUID) -> str:
    """
    Checks Valkey for key 'mower:{mower_id}:owner'.
    If cache hit, refreshes its TTL to 24 hours and returns the owner_id or "dne".
    If cache miss, queries Postgres. Caches the result in Valkey with 24hr TTL.
    Returns the owner_id, "dne", or "fail".
    """
    mower_uuid_str = str(mower_id).strip().lower()
    valkey_key = f"mower:{mower_uuid_str}:owner"

    v_client = get_valkey_client()
    try:
        # 1. Check Valkey cache
        cached_owner = await v_client.get(valkey_key)
        if cached_owner is not None:
            logger.info(f"Valkey cache hit for mower owner key: {valkey_key}")
            # Refresh expire time back to 24hr (86400 seconds)
            await v_client.expire(valkey_key, 86400)
            return cached_owner
    except Exception as valkey_err:
        logger.error(f"Valkey error during mower owner check: {valkey_err}")
    finally:
        await v_client.close()

    # Convert mower_id to UUID object for SQLAlchemy query
    try:
        m_uuid = (
            uuid.UUID(mower_uuid_str)
            if isinstance(mower_id, str)
            else mower_id
        )
    except ValueError as val_err:
        logger.error(f"Invalid UUID format '{mower_uuid_str}': {val_err}")
        return "dne"

    # 2. Cache miss: check PostgreSQL
    logger.info(
        f"Valkey cache miss for key {valkey_key}. Checking PostgreSQL..."
    )
    owner_id_result = "dne"
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MowerModel.owner_id).where(MowerModel.id == m_uuid)
            result = await session.execute(stmt)
            row = result.fetchone()

            if not row:
                owner_id_result = "dne"
            else:
                owner_id_result = row[0] if row[0] is not None else "dne"
    except Exception as db_err:
        logger.error(
            "Database lookup failed for mower %s: %s",
            mower_uuid_str,
            db_err,
            exc_info=True,
        )
        return "fail"

    # 3. Populate Valkey cache with 24hr expiration
    v_client = get_valkey_client()
    try:
        await v_client.setex(valkey_key, 86400, owner_id_result)
        logger.info(
            f"Cached owner result '{owner_id_result}' in Valkey under key: {valkey_key}"
        )
    except Exception as valkey_err:
        logger.error(f"Failed to cache owner result in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return owner_id_result
