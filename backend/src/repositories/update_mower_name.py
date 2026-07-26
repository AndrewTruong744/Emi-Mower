import logging
import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import MowerNotFoundError, RepositoryError
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.update_mower_name")


async def update_mower_name(
    mower_id: str | uuid.UUID, new_name: str, db: AsyncSession
) -> None:
    """
    Updates the nickname/name of a mower in PostgreSQL using provided AsyncSession.
    Also invalidates the cached mower data in Valkey.
    Raises MowerNotFoundError if mower does not exist, or RepositoryError on DB error.
    """
    logger.info(f"Updating mower {mower_id} nickname to: {new_name}")
    try:
        m_uuid = uuid.UUID(mower_id) if isinstance(mower_id, str) else mower_id
    except ValueError as val_err:
        logger.error(f"Invalid mower ID format: {val_err}")
        raise MowerNotFoundError(f"Invalid mower ID format: {mower_id}") from val_err

    # 1. Update database
    try:
        stmt = (
            update(MowerModel).where(MowerModel.id == m_uuid).values(nickname=new_name)
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            logger.warning(f"No mower found with ID {m_uuid}")
            raise MowerNotFoundError(f"No mower found with ID {mower_id}")
        await db.commit()
    except MowerNotFoundError:
        raise
    except Exception as db_err:
        logger.error(
            f"Failed to update mower nickname in Postgres: {db_err}",
            exc_info=True,
        )
        await db.rollback()
        raise RepositoryError(f"Failed to update mower {mower_id} nickname") from db_err

    # 2. Invalidate Valkey cache for this mower
    try:
        async with get_valkey_client() as v_client:
            cache_key = f"mower:{m_uuid}:data"
            await v_client.delete(cache_key)
            logger.info(f"Invalidated Valkey cache key '{cache_key}'")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
