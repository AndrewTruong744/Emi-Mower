import json
import logging

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.user import UserModel

logger = logging.getLogger("repositories.create_user")


async def create_user(user_id: str, email: str, name: str) -> dict | str:
    """
    Creates a new user in PostgreSQL and caches the user object in Valkey
    under the key 'user:{user_id}:data' with a 24-hour expiration time.
    Returns the user data dict or "fail".
    """
    logger.info(f"Creating user in Postgres: {user_id}")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                new_user = UserModel(id=user_id, email=email, name=name)
                session.add(new_user)
            await session.refresh(new_user)
            user_data = {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "created_at": (
                    new_user.created_at.isoformat()
                    if new_user.created_at
                    else None
                ),
            }
    except Exception as db_err:
        logger.error(
            f"Failed to create user in database: {db_err}", exc_info=True
        )
        return "fail"

    # Save to Valkey with 24-hour expiration
    v_client = get_valkey_client()
    try:
        valkey_key = f"user:{user_id}:data"
        await v_client.setex(valkey_key, 86400, json.dumps(user_data))
        logger.info(f"Cached user data in Valkey under key '{valkey_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to cache user data in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return user_data
