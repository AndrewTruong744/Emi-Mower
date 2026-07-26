import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.user import UserModel

logger = logging.getLogger("repositories.create_user")


async def create_user(user_id: str, email: str, name: str, db: AsyncSession) -> dict:
    """
    Creates a new user in PostgreSQL using the provided AsyncSession
    and caches the user object in Valkey under the key 'user:{user_id}:data'.
    Raises RepositoryError on database failure.
    """
    logger.info(f"Creating user in Postgres: {user_id}")
    try:
        new_user = UserModel(id=user_id, email=email, name=name)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user_data = {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "created_at": (
                new_user.created_at.isoformat() if new_user.created_at else None
            ),
        }
    except Exception as db_err:
        logger.error(f"Failed to create user in database: {db_err}", exc_info=True)
        await db.rollback()
        raise RepositoryError(
            f"Failed to create user {user_id} in database"
        ) from db_err

    # Save to Valkey with 24-hour expiration
    try:
        async with get_valkey_client() as v_client:
            valkey_key = f"user:{user_id}:data"
            await v_client.setex(valkey_key, 86400, json.dumps(user_data))
            logger.info(f"Cached user data in Valkey under key '{valkey_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to cache user data in Valkey: {valkey_err}")

    return user_data
