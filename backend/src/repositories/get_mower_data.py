import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.get_mower_data")


async def get_mower_data(user_id: str, db: AsyncSession) -> list[dict]:
    """
    Retrieves all mower data owned by a user using a cache-aside pattern.
    Raises RepositoryError on database failure.
    """
    valkey_user_mowers_key = f"user:{user_id}:mowers"

    try:
        async with get_valkey_client() as v_client:
            cached_mower_ids = await v_client.get(valkey_user_mowers_key)
            if cached_mower_ids:
                mower_ids = json.loads(cached_mower_ids)
                pipeline = v_client.pipeline()
                for m_id in mower_ids:
                    pipeline.get(f"mower:{m_id}:data")
                    pipeline.get(f"mower:{m_id}:status")

                pipeline_results = await pipeline.execute()

                all_cached = True
                mowers_list = []
                for i in range(len(mower_ids)):
                    mower_data_str = pipeline_results[i * 2]
                    status_str = pipeline_results[i * 2 + 1]
                    if mower_data_str is None:
                        all_cached = False
                        break

                    m_data = json.loads(mower_data_str)
                    m_data["status"] = "online" if status_str == "online" else "offline"
                    mowers_list.append(m_data)

                if all_cached:
                    logger.info(f"Valkey cache hit for all mowers of user {user_id}")
                    pipeline = v_client.pipeline()
                    pipeline.expire(valkey_user_mowers_key, 86400)
                    for m_id in mower_ids:
                        pipeline.expire(f"mower:{m_id}:data", 86400)
                    await pipeline.execute()
                    return mowers_list
    except Exception as e:
        logger.error(f"Valkey error during mower data lookup: {e}")

    # Cache miss: query Postgres
    logger.info(f"Valkey cache miss for mowers of user {user_id}. Querying Postgres...")
    try:
        stmt = select(MowerModel).where(MowerModel.owner_id == user_id)
        result = await db.execute(stmt)
        mowers = result.scalars().all()

        mowers_list = []
        mower_ids = []
        for m in mowers:
            m_id_str = str(m.id)
            mower_ids.append(m_id_str)
            mowers_list.append(
                {
                    "id": m_id_str,
                    "serial_number": m.serial_number,
                    "nickname": m.nickname,
                    "owner_id": m.owner_id,
                }
            )
    except Exception as db_err:
        logger.error(
            f"Postgres query failed for mowers of user {user_id}: {db_err}",
            exc_info=True,
        )
        raise RepositoryError(
            f"Failed to query mower data for user '{user_id}'"
        ) from db_err

    # Save to Valkey
    try:
        async with get_valkey_client() as v_client:
            await v_client.setex(valkey_user_mowers_key, 86400, json.dumps(mower_ids))

            pipeline = v_client.pipeline()
            for m_data in mowers_list:
                m_id = m_data["id"]
                pipeline.setex(f"mower:{m_id}:data", 86400, json.dumps(m_data))
                pipeline.get(f"mower:{m_id}:status")

            status_results = await pipeline.execute()

            for idx, m_data in enumerate(mowers_list):
                status_val = status_results[idx * 2 + 1]
                m_data["status"] = "online" if status_val == "online" else "offline"

            logger.info(f"Cached mowers data in Valkey for user {user_id}")
    except Exception as valkey_err:
        logger.error(f"Failed to cache mowers data in Valkey: {valkey_err}")
        for m_data in mowers_list:
            if "status" not in m_data:
                m_data["status"] = "offline"

    return mowers_list
