import logging

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError, UserNotFoundError
from src.models.user import UserModel
from src.schemas.valkey import user_data_key

logger = logging.getLogger("repositories.update_user_name")


async def update_user_name(user_id: str, new_user_name: str, db: AsyncSession) -> None:
    """
    Updates the name of a user in PostgreSQL using provided AsyncSession.
    Also invalidates the cached user data in Valkey.
    Raises UserNotFoundError if user does not exist, or RepositoryError on DB failure.
    """
    logger.info(f"Updating user {user_id} name to: {new_user_name}")
    try:
        stmt = (
            update(UserModel).where(UserModel.id == user_id).values(name=new_user_name)
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            logger.warning(f"No user found with ID {user_id}")
            raise UserNotFoundError(f"No user found with ID {user_id}")
        await db.commit()
    except UserNotFoundError:
        raise
    except Exception as db_err:
        logger.error(f"Failed to update user name in Postgres: {db_err}", exc_info=True)
        await db.rollback()
        raise RepositoryError(f"Failed to update name for user {user_id}") from db_err

    # Invalidate Valkey cache for this user
    try:
        async with get_valkey_client() as v_client:
            cache_key = user_data_key(user_id)
            await v_client.delete(cache_key)
            logger.info(f"Invalidated Valkey cache key '{cache_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
