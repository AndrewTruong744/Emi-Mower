import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import MowerNotFoundError, RepositoryError, UserNotFoundError
from src.models.mower import MowerModel
from src.models.user import UserModel
from src.schemas.valkey import mower_data_key, user_mowers_key

logger = logging.getLogger("repositories.set_mower_owner")


async def set_mower_owner(
    owner_id: str | None, mower_id: uuid.UUID, db: AsyncSession
) -> None:
    """
    Updates the owner of a mower in PostgreSQL using provided AsyncSession.
    Also invalidates cached mower details and the mower list for both the new
    owner and the old owner (if changed).
    Raises MowerNotFoundError if mower does not exist, UserNotFoundError if a
    requested owner does not exist, or RepositoryError on DB error.
    """
    logger.info("Setting mower %s owner to %s", mower_id, owner_id)

    old_owner_id = None

    try:
        # 1. Fetch current mower to identify the old owner
        stmt_select = select(MowerModel.owner_id).where(MowerModel.id == mower_id)
        result_select = await db.execute(stmt_select)
        row = result_select.fetchone()
        if not row:
            logger.warning(f"No mower found with ID {mower_id}")
            raise MowerNotFoundError(f"No mower found with ID {mower_id}")
        old_owner_id = row[0]

        if owner_id is not None:
            user_result = await db.execute(
                select(UserModel.id).where(UserModel.id == owner_id)
            )
            if user_result.scalar_one_or_none() is None:
                logger.warning(f"No user found with ID {owner_id}")
                raise UserNotFoundError(f"No user found with ID {owner_id}")

        # 2. Update the owner_id
        stmt_update = (
            update(MowerModel)
            .where(MowerModel.id == mower_id)
            .values(owner_id=owner_id)
        )
        await db.execute(stmt_update)
        await db.commit()
    except (MowerNotFoundError, UserNotFoundError):
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
            pipeline.delete(mower_data_key(str(mower_id)))

            # Evict mowers list cache for new owner
            if owner_id:
                pipeline.delete(user_mowers_key(owner_id))

            # Evict mowers list cache for old owner
            if old_owner_id and old_owner_id != owner_id:
                pipeline.delete(user_mowers_key(old_owner_id))

            await pipeline.execute()
            logger.info(f"Evicted Valkey cache keys for mower {mower_id}")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
