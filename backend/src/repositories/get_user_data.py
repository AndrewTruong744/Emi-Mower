import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError, UserNotFoundError
from src.models.user import UserModel

logger = logging.getLogger("repositories.get_user_data")


async def get_user_data(user_id: str, db: AsyncSession) -> dict:
    """
    Retrieves user data using a cache-aside pattern.
    Checks Valkey key 'user:{user_id}:data' first.
    If hit, refreshes expiration to 24hr and returns it.
    If miss, queries PostgreSQL via provided AsyncSession and populates Valkey.
    Raises UserNotFoundError if user is not found, or RepositoryError on DB failure.
    """
    valkey_key = f"user:{user_id}:data"

    try:
        # 1. Check Valkey
        async with get_valkey_client() as v_client:
            cached = await v_client.get(valkey_key)
            if cached is not None:
                logger.info(f"Valkey cache hit for user data key: {valkey_key}")
                try:
                    user_data = json.loads(cached)
                    await v_client.expire(valkey_key, 86400)
                    return user_data
                except Exception as parse_err:
                    logger.error(f"Failed to parse cached user data JSON: {parse_err}")
    except Exception as valkey_err:
        logger.error(f"Valkey error during user data lookup: {valkey_err}")

    # 2. Cache miss: Check PostgreSQL
    logger.info(f"Valkey cache miss. Querying Postgres for user: {user_id}")
    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User '{user_id}' not found in PostgreSQL")
            raise UserNotFoundError(f"User '{user_id}' not found")

        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "created_at": (user.created_at.isoformat() if user.created_at else None),
        }
    except UserNotFoundError:
        raise
    except Exception as db_err:
        logger.error(
            "Postgres query failed for user %s: %s",
            user_id,
            db_err,
            exc_info=True,
        )
        raise RepositoryError(f"Database query failed for user '{user_id}'") from db_err

    # 3. Populate Valkey cache with 24hr expiration
    try:
        async with get_valkey_client() as v_client:
            await v_client.setex(valkey_key, 86400, json.dumps(user_data))
            logger.info(f"Cached user data in Valkey under key: {valkey_key}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache user data in Valkey: {valkey_err}")

    return user_data
