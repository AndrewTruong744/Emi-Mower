import json
import logging
import uuid

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.verify_ownership")


async def verify_ownership(user_id: str, mower_uuid: str | uuid.UUID) -> bool:
    """
    Verifies if a user owns a given mower using a cache-aside pattern.
    Checks Valkey first under 'user-{userId}-mowers'.
    On cache miss, queries Postgres and populates the Valkey cache.
    """
    mower_uuid_str = str(mower_uuid).strip().lower()
    valkey_key = f"user-{user_id}-mowers"

    v_client = get_valkey_client()
    try:
        # 1. Check Valkey cache
        cached_data = await v_client.get(valkey_key)
        if cached_data is not None:
            try:
                mower_list = json.loads(cached_data)
                if isinstance(mower_list, list):
                    logger.info(f"Cache hit for key {valkey_key}")
                    normalized_list = [str(m).strip().lower() for m in mower_list]
                    return mower_uuid_str in normalized_list
            except Exception as e:
                logger.error(f"Failed to parse cached mowers JSON: {e}")
                # Fall through to DB on cache parse error
    except Exception as e:
        logger.error(f"Valkey error during ownership check: {e}")
    finally:
        await v_client.close()

    # 2. Cache miss or error: query database
    logger.info(f"Cache miss for key {valkey_key}. Checking PostgreSQL...")
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MowerModel.id).where(MowerModel.owner_id == user_id)
            result = await session.execute(stmt)
            mower_ids = result.scalars().all()

            mower_strings = [str(m_id).strip().lower() for m_id in mower_ids]

            # Populate Valkey cache (with 1 hour TTL)
            v_client = get_valkey_client()
            try:
                await v_client.setex(valkey_key, 3600, json.dumps(mower_strings))
                logger.info(f"Populated Valkey cache for key {valkey_key}")
            except Exception as cache_err:
                logger.error(f"Failed to populate Valkey cache: {cache_err}")
            finally:
                await v_client.close()

            return mower_uuid_str in mower_strings

    except Exception as db_err:
        logger.error(
            f"Database error during ownership verification: {db_err}",
            exc_info=True,
        )
        return False
