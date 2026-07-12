import logging
import uuid

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.check_mower_ownership")


async def check_mower_ownership(mower_id: str) -> str | None:
    """
    Checks Valkey for key 'mower:{mower_id}:owner'.
    If cache hit, refreshes TTL to 24hr and returns the owner user_id or None.
    If cache miss, queries Postgres. Caches the result in Valkey with 24hr TTL.
    Returns the user_id (str), None (if not owned/dne), or "fail".
    """
    mower_uuid_str = str(mower_id).strip().lower()
    valkey_key = f"mower:{mower_uuid_str}:owner"

    v_client = get_valkey_client()
    try:
        cached = await v_client.get(valkey_key)
        if cached is not None:
            logger.info(f"Valkey hit for mower owner: {valkey_key}")
            await v_client.expire(valkey_key, 86400)
            if cached in ("dne", "none", ""):
                return None
            return cached
    except Exception as valkey_err:
        logger.error(f"Valkey error during ownership lookup: {valkey_err}")
    finally:
        await v_client.close()

    try:
        m_uuid = uuid.UUID(mower_uuid_str)
    except ValueError as val_err:
        logger.error(f"Invalid UUID format '{mower_uuid_str}': {val_err}")
        return None

    # Cache miss: query Postgres
    logger.info(
        f"Valkey cache miss for key {valkey_key}. Checking PostgreSQL..."
    )
    owner_id = None
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MowerModel.owner_id).where(MowerModel.id == m_uuid)
            result = await session.execute(stmt)
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
        return "fail"

    # Cache results in Valkey
    v_client = get_valkey_client()
    try:
        cache_value = owner_id if owner_id is not None else "dne"
        await v_client.setex(valkey_key, 86400, cache_value)
        logger.info(
            f"Cached ownership '{cache_value}' under Valkey key: {valkey_key}"
        )
    except Exception as valkey_err:
        logger.error(f"Failed to cache ownership in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return owner_id
