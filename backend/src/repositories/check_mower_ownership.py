"""Ownership lookup backed by the shared mower-data cache entry."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel
from src.schemas.valkey import VALKEY_CACHE_TTL_SECONDS, MowerDataCache, mower_data_key

logger = logging.getLogger("repositories.check_mower_ownership")


async def check_mower_ownership(mower_id: uuid.UUID, db: AsyncSession) -> str | None:
    """Return a mower's owner from ``mower:{id}:data`` or PostgreSQL.

    A mower's data entry already contains ``owner_id``. Reusing it prevents a
    second owner-only Valkey projection from becoming stale independently.
    """
    cache_key = mower_data_key(str(mower_id))
    try:
        async with get_valkey_client() as v_client:
            cached = await v_client.get(cache_key)
            if cached is not None:
                mower_data = MowerDataCache.model_validate_json(cached)
                await v_client.expire(cache_key, VALKEY_CACHE_TTL_SECONDS)
                logger.info("Valkey hit for mower data: %s", cache_key)
                return mower_data.owner_id
    except Exception as valkey_err:
        logger.warning("Valkey error during ownership lookup: %s", valkey_err)

    logger.info("Valkey cache miss for mower data %s; checking PostgreSQL", cache_key)
    try:
        result = await db.execute(select(MowerModel).where(MowerModel.id == mower_id))
        mower = result.scalar_one_or_none()
    except Exception as db_err:
        logger.error("Database lookup failed for mower %s", mower_id, exc_info=True)
        raise RepositoryError(
            f"Database lookup failed for mower '{mower_id}'"
        ) from db_err

    if mower is None:
        return None

    mower_data = MowerDataCache(
        id=str(mower.id),
        nickname=mower.nickname,
        owner_id=mower.owner_id,
    )
    try:
        async with get_valkey_client() as v_client:
            await v_client.setex(
                mower_data_key(mower_data.id),
                VALKEY_CACHE_TTL_SECONDS,
                mower_data.model_dump_json(),
            )
    except Exception as valkey_err:
        logger.warning(
            "Failed to cache mower data for ownership lookup: %s", valkey_err
        )

    return mower_data.owner_id
