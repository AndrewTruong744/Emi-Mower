import logging

from sqlalchemy import update

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.user import UserModel

logger = logging.getLogger("repositories.update_user_name")


async def update_user_name(user_id: str, new_user_name: str) -> str:
    """
    Updates the name of a user in PostgreSQL.
    Also invalidates the cached user data in Valkey.
    Returns "success" or "fail".
    """
    logger.info(f"Updating user {user_id} name to: {new_user_name}")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = (
                    update(UserModel)
                    .where(UserModel.id == user_id)
                    .values(name=new_user_name)
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logger.warning(f"No user found with ID {user_id}")
                    return "fail"
            await session.commit()
    except Exception as db_err:
        logger.error(
            f"Failed to update user name in Postgres: {db_err}", exc_info=True
        )
        return "fail"

    # Invalidate Valkey cache for this user
    v_client = get_valkey_client()
    try:
        cache_key = f"user:{user_id}:data"
        await v_client.delete(cache_key)
        logger.info(f"Invalidated Valkey cache key '{cache_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return "success"
