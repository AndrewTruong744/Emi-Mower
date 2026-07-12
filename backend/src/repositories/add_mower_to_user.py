import logging
import uuid

from sqlalchemy import select, update

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.add_mower_to_user")


async def add_mower_to_user(user_id: str | None, mower_id: str) -> str:
    """
    Updates the owner of a mower in PostgreSQL.
    Also invalidates the cached mower owner key, mower details, and the
    mower list for both the new owner and the old owner (if changed).
    Returns "success" or "fail".
    """
    logger.info(f"Adding mower {mower_id} to user: {user_id}")
    try:
        m_uuid = uuid.UUID(str(mower_id).strip().lower())
    except ValueError as val_err:
        logger.error(f"Invalid mower ID format: {val_err}")
        return "fail"

    old_owner_id = None

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # 1. Fetch current mower to identify the old owner
                stmt_select = select(MowerModel.owner_id).where(
                    MowerModel.id == m_uuid
                )
                result_select = await session.execute(stmt_select)
                row = result_select.fetchone()
                if not row:
                    logger.warning(f"No mower found with ID {m_uuid}")
                    return "fail"
                old_owner_id = row[0]

                # 2. Update the owner_id
                stmt_update = (
                    update(MowerModel)
                    .where(MowerModel.id == m_uuid)
                    .values(owner_id=user_id)
                )
                await session.execute(stmt_update)

            await session.commit()
    except Exception as db_err:
        logger.error(
            f"Failed to update mower owner in Postgres: {db_err}", exc_info=True
        )
        return "fail"

    # 3. Invalidate Valkey cache keys
    v_client = get_valkey_client()
    try:
        pipeline = v_client.pipeline()

        # Evict individual mower info
        pipeline.delete(f"mower:{m_uuid}:owner")
        pipeline.delete(f"mower:{m_uuid}:data")

        # Evict mowers list cache for new owner
        if user_id:
            pipeline.delete(f"user:{user_id}:mowers")

        # Evict mowers list cache for old owner
        if old_owner_id and old_owner_id != user_id:
            pipeline.delete(f"user:{old_owner_id}:mowers")

        await pipeline.execute()
        logger.info(f"Evicted Valkey cache keys for mower {m_uuid}")
    except Exception as valkey_err:
        logger.error(f"Failed to invalidate cache in Valkey: {valkey_err}")
    finally:
        await v_client.close()

    return "success"
