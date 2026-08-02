import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import MowerNotFoundError, RepositoryError
from src.models.mower import MowerModel
from src.schemas.valkey import mower_data_key, mower_owner_key, user_mowers_key

logger = logging.getLogger("repositories.add_mower_to_user")


async def add_mower_to_user(
    user_id: str | None, mower_id: str, db: AsyncSession
) -> None:
    """
    Updates the owner of a mower in PostgreSQL using provided AsyncSession.
    Also invalidates the cached mower owner key, mower details, and the
    mower list for both the new owner and the old owner (if changed).
    Raises MowerNotFoundError if mower does not exist, or RepositoryError on DB error.
    """
    logger.info(f"Adding mower {mower_id} to user: {user_id}")
    try:
        m_uuid = uuid.UUID(str(mower_id).strip().lower())
    except ValueError as val_err:
        logger.error(f"Invalid mower ID format: {val_err}")
        raise MowerNotFoundError(f"Invalid mower ID format: {mower_id}") from val_err

    old_owner_id = None

    try:
        # 1. Fetch current mower to identify the old owner
        stmt_select = select(MowerModel.owner_id).where(MowerModel.id == m_uuid)
        result_select = await db.execute(stmt_select)
        row = result_select.fetchone()
        if not row:
            logger.warning(f"No mower found with ID {m_uuid}")
            raise MowerNotFoundError(f"No mower found with ID {mower_id}")
        old_owner_id = row[0]

        # 2. Update the owner_id
        stmt_update = (
            update(MowerModel).where(MowerModel.id == m_uuid).values(owner_id=user_id)
        )
        await db.execute(stmt_update)
        await db.commit()
    except MowerNotFoundError:
        raise
    except Exception as db_err:
        logger.error(
            f"Failed to update mower owner in Postgres: {db_err}", exc_info=True
        )
        await db.rollback()
        raise RepositoryError(
            f"Failed to update mower {mower_id} ownership"
        ) from db_err

    # 3. Invalidate Valkey cache keys
    try:
        async with get_valkey_client() as v_client:
            pipeline = v_client.pipeline()

            # Evict individual mower info
            pipeline.delete(mower_owner_key(str(m_uuid)))
            pipeline.delete(mower_data_key(str(m_uuid)))

            # Evict mowers list cache for new owner
            if user_id:
                pipeline.delete(user_mowers_key(user_id))

            # Evict mowers list cache for old owner
            if old_owner_id and old_owner_id != user_id:
                pipeline.delete(user_mowers_key(old_owner_id))

            await pipeline.execute()
            logger.info(f"Evicted Valkey cache keys for mower {m_uuid}")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
