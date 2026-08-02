import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel
from src.schemas.valkey import (
    VALKEY_CACHE_TTL_SECONDS,
    MowerDataCache,
    MowerStatusCache,
    UserMowersCache,
    mower_data_key,
    mower_status_key,
    user_mowers_key,
)

logger = logging.getLogger("repositories.get_mower_data")


def _status_value(status: str | None) -> str:
    if status is None:
        return "offline"
    return (
        "online"
        if MowerStatusCache.model_validate(status).root == "online"
        else "offline"
    )


async def get_mower_data(user_id: str, db: AsyncSession) -> list[dict]:
    """Retrieve all mower data owned by a user using the Valkey schema."""
    user_mowers_cache_key = user_mowers_key(user_id)

    try:
        async with get_valkey_client() as v_client:
            cached_mower_ids = await v_client.get(user_mowers_cache_key)
            if cached_mower_ids is not None:
                mower_ids = UserMowersCache.model_validate_json(cached_mower_ids).root
                pipeline = v_client.pipeline()
                for mower_id in mower_ids:
                    pipeline.get(mower_data_key(mower_id))
                    pipeline.get(mower_status_key(mower_id))

                pipeline_results = await pipeline.execute()
                mowers_list = []
                for index, mower_id in enumerate(mower_ids):
                    mower_data_value = pipeline_results[index * 2]
                    status_value = pipeline_results[index * 2 + 1]
                    if mower_data_value is None:
                        break
                    mower_data = MowerDataCache.model_validate_json(mower_data_value)
                    mower_dict = mower_data.model_dump(mode="json")
                    mower_dict["status"] = _status_value(status_value)
                    mowers_list.append(mower_dict)
                else:
                    logger.info("Valkey cache hit for all mowers of user %s", user_id)
                    pipeline = v_client.pipeline()
                    pipeline.expire(user_mowers_cache_key, VALKEY_CACHE_TTL_SECONDS)
                    for mower_id in mower_ids:
                        pipeline.expire(
                            mower_data_key(mower_id), VALKEY_CACHE_TTL_SECONDS
                        )
                    await pipeline.execute()
                    return mowers_list
    except Exception as err:
        logger.error("Valkey error during mower data lookup: %s", err)

    logger.info("Valkey cache miss for mowers of user %s", user_id)
    try:
        result = await db.execute(
            select(MowerModel).where(MowerModel.owner_id == user_id)
        )
        mowers = result.scalars().all()
        mower_ids = [str(mower.id) for mower in mowers]
        mower_cache_values = [
            MowerDataCache(
                id=str(mower.id),
                serial_number=mower.serial_number,
                nickname=mower.nickname,
                owner_id=mower.owner_id,
            )
            for mower in mowers
        ]
    except Exception as db_err:
        logger.error(
            "Postgres query failed for mowers of user %s: %s",
            user_id,
            db_err,
            exc_info=True,
        )
        raise RepositoryError(
            f"Failed to query mower data for user '{user_id}'"
        ) from db_err

    try:
        async with get_valkey_client() as v_client:
            await v_client.setex(
                user_mowers_cache_key,
                VALKEY_CACHE_TTL_SECONDS,
                UserMowersCache(mower_ids).model_dump_json(),
            )
            pipeline = v_client.pipeline()
            for mower_data in mower_cache_values:
                pipeline.setex(
                    mower_data_key(mower_data.id),
                    VALKEY_CACHE_TTL_SECONDS,
                    mower_data.model_dump_json(),
                )
                pipeline.get(mower_status_key(mower_data.id))

            status_results = await pipeline.execute()
            mowers_list = []
            for index, mower_data in enumerate(mower_cache_values):
                mower_dict = mower_data.model_dump(mode="json")
                mower_dict["status"] = _status_value(status_results[index * 2 + 1])
                mowers_list.append(mower_dict)
            logger.info("Cached mowers data for user %s", user_id)
            return mowers_list
    except Exception as valkey_err:
        logger.error("Failed to cache mowers data in Valkey: %s", valkey_err)
        return [
            {
                **mower_data.model_dump(mode="json"),
                "status": "offline",
            }
            for mower_data in mower_cache_values
        ]
