import json
import logging

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.get_mowers_of_user")


async def get_mowers_of_user(user_id: str) -> list | str:
    """
    Retrieves the list of mowers owned by a user using the cache-aside pattern.
    Key: user:{user_id}:mowers
    Returns a list of mower IDs or "fail" on error.
    """
    valkey_user_mowers_key = f"user:{user_id}:mowers"
    v_client = get_valkey_client()

    try:
        cached_mower_ids = await v_client.get(valkey_user_mowers_key)
        if cached_mower_ids:
            mower_ids = json.loads(cached_mower_ids)
            logger.info(f"Valkey cache hit for mowers of user {user_id}")
            # Refresh expiration back to 86400 seconds (24h)
            await v_client.expire(valkey_user_mowers_key, 86400)
            return mower_ids
    except Exception as valkey_err:
        logger.error(
            f"Valkey error during mower lookup for user {user_id}: {valkey_err}"
        )
    finally:
        await v_client.close()

    # Cache miss: query Postgres
    logger.info(f"Valkey cache miss for mowers of user {user_id}. Querying Postgres...")
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MowerModel.id).where(MowerModel.owner_id == user_id)
            result = await session.execute(stmt)
            mower_uuids = result.scalars().all()
            mower_ids = [str(m_id) for m_id in mower_uuids]
    except Exception as db_err:
        logger.error(
            f"Postgres query failed for mowers of user {user_id}: {db_err}",
            exc_info=True,
        )
        return "fail"

    # Save to Valkey cache
    v_client = get_valkey_client()
    try:
        await v_client.setex(valkey_user_mowers_key, 86400, json.dumps(mower_ids))
        logger.info(f"Cached mowers list in Valkey for user {user_id}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache mowers list in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return mower_ids
