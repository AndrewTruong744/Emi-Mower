import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.get_mowers_of_user")


async def get_mowers_of_user(user_id: str, db: AsyncSession) -> list[str]:
    """
    Retrieves the list of mowers owned by a user using the cache-aside pattern.
    Key: user:{user_id}:mowers
    Returns a list of mower IDs or raises RepositoryError.
    """
    valkey_user_mowers_key = f"user:{user_id}:mowers"

    try:
        async with get_valkey_client() as v_client:
            cached_mower_ids = await v_client.get(valkey_user_mowers_key)
            if cached_mower_ids:
                mower_ids = json.loads(cached_mower_ids)
                logger.info(f"Valkey cache hit for mowers of user {user_id}")
                await v_client.expire(valkey_user_mowers_key, 86400)
                return mower_ids
    except Exception as valkey_err:
        logger.error(
            f"Valkey error during mower lookup for user {user_id}: {valkey_err}"
        )

    # Cache miss: query Postgres
    logger.info(f"Valkey cache miss for mowers of user {user_id}. Querying Postgres...")
    try:
        stmt = select(MowerModel.id).where(MowerModel.owner_id == user_id)
        result = await db.execute(stmt)
        mower_uuids = result.scalars().all()
        mower_ids = [str(m_id) for m_id in mower_uuids]
    except Exception as db_err:
        logger.error(
            f"Postgres query failed for mowers of user {user_id}: {db_err}",
            exc_info=True,
        )
        raise RepositoryError(
            f"Failed to query mowers for user '{user_id}'"
        ) from db_err

    # Save to Valkey cache
    try:
        async with get_valkey_client() as v_client:
            await v_client.setex(valkey_user_mowers_key, 86400, json.dumps(mower_ids))
            logger.info(f"Cached mowers list in Valkey for user {user_id}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache mowers list in Valkey: {valkey_err}")

    return mower_ids
