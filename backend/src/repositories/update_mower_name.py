import logging
import uuid

from sqlalchemy import update

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.update_mower_name")


async def update_mower_name(mower_id: str | uuid.UUID, new_name: str) -> str:
    """
    Updates the nickname/name of a mower in PostgreSQL.
    Also invalidates the cached mower data in Valkey.
    Returns "success" or "fail".
    """
    logger.info(f"Updating mower {mower_id} nickname to: {new_name}")
    try:
        m_uuid = (
            uuid.UUID(mower_id) if isinstance(mower_id, str) else mower_id
        )
    except ValueError as val_err:
        logger.error(f"Invalid mower ID format: {val_err}")
        return "fail"

    # 1. Update database
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = (
                    update(MowerModel)
                    .where(MowerModel.id == m_uuid)
                    .values(nickname=new_name)
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    logger.warning(f"No mower found with ID {m_uuid}")
                    return "fail"
            await session.commit()
    except Exception as db_err:
        logger.error(
            f"Failed to update mower nickname in Postgres: {db_err}",
            exc_info=True,
        )
        return "fail"

    # 2. Invalidate Valkey cache for this mower
    v_client = get_valkey_client()
    try:
        cache_key = f"mower:{m_uuid}:data"
        await v_client.delete(cache_key)
        logger.info(f"Invalidated Valkey cache key '{cache_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return "success"
