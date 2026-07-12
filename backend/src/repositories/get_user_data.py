import json
import logging

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.user import UserModel

logger = logging.getLogger("repositories.get_user_data")


async def get_user_data(user_id: str) -> dict | str:
    """
    Retrieves user data using a cache-aside pattern.
    Checks Valkey key 'user:{user_id}:data' first.
    If hit, refreshes expiration to 24hr and returns it.
    If miss, queries PostgreSQL, populates Valkey, and returns the data.
    Returns the user data dict or "fail".
    """
    valkey_key = f"user:{user_id}:data"
    v_client = get_valkey_client()

    try:
        # 1. Check Valkey
        cached = await v_client.get(valkey_key)
        if cached:
            logger.info(f"Valkey cache hit for user data key: {valkey_key}")
            try:
                user_data = json.loads(cached)
                # Refresh expire time back to 24hr (86400 seconds)
                await v_client.expire(valkey_key, 86400)
                return user_data
            except Exception as parse_err:
                logger.error(f"Failed to parse cached user data JSON: {parse_err}")
                # Fall through to db on corrupt cache
    except Exception as valkey_err:
        logger.error(f"Valkey error during user data lookup: {valkey_err}")
    finally:
        await v_client.close()

    # 2. Cache miss: Check PostgreSQL
    logger.info(f"Valkey cache miss. Querying Postgres for user: {user_id}")
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"User '{user_id}' not found in PostgreSQL")
                return "fail"

            user_data = {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "created_at": (
                    user.created_at.isoformat()
                    if user.created_at
                    else None
                ),
            }
    except Exception as db_err:
        logger.error(
            "Postgres query failed for user %s: %s",
            user_id,
            db_err,
            exc_info=True,
        )
        return "fail"

    # 3. Populate Valkey cache with 24hr expiration
    v_client = get_valkey_client()
    try:
        await v_client.setex(valkey_key, 86400, json.dumps(user_data))
        logger.info(f"Cached user data in Valkey under key: {valkey_key}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache user data in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return user_data
