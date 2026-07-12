import json
import logging

from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerModel

logger = logging.getLogger("repositories.get_mower_data")


async def get_mower_data(user_id: str) -> list | str:
    """
    Retrieves all mower data owned by a user using a cache-aside pattern.
    1. Checks Valkey key 'user:{user_id}:mowers' for mower IDs.
    2. If found, pipeline gets mower data and status. Updates expire time.
    3. If cache miss, queries Postgres, caches data, and returns the result.
    4. For each mower, sets status to online if 'status' key exists, else offline.
    Returns a list of mower data dicts or "fail".
    """
    valkey_user_mowers_key = f"user:{user_id}:mowers"
    v_client = get_valkey_client()

    try:
        cached_mower_ids = await v_client.get(valkey_user_mowers_key)
        if cached_mower_ids:
            mower_ids = json.loads(cached_mower_ids)
            # Pipelined get for each mower data and status
            pipeline = v_client.pipeline()
            for m_id in mower_ids:
                pipeline.get(f"mower:{m_id}:data")
                pipeline.get(f"mower:{m_id}:status")

            pipeline_results = await pipeline.execute()

            # Verify if we got all mower data from Valkey.
            all_cached = True
            mowers_list = []
            for i in range(len(mower_ids)):
                mower_data_str = pipeline_results[i * 2]
                status_str = pipeline_results[i * 2 + 1]
                if mower_data_str is None:
                    all_cached = False
                    break

                m_data = json.loads(mower_data_str)
                # Check if the mower:{mower_id}:status key exists
                m_data["status"] = (
                    "online" if status_str == "online" else "offline"
                )
                mowers_list.append(m_data)

            if all_cached:
                logger.info(
                    f"Valkey cache hit for all mowers of user {user_id}"
                )
                # Refresh expire times back to 24hr (86400 seconds)
                pipeline = v_client.pipeline()
                pipeline.expire(valkey_user_mowers_key, 86400)
                for m_id in mower_ids:
                    pipeline.expire(f"mower:{m_id}:data", 86400)
                await pipeline.execute()
                return mowers_list
    except Exception as e:
        logger.error(f"Valkey error during mower data lookup: {e}")
    finally:
        await v_client.close()

    # Cache miss: query Postgres
    logger.info(
        f"Valkey cache miss for mowers of user {user_id}. Querying Postgres..."
    )
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(MowerModel).where(MowerModel.owner_id == user_id)
            result = await session.execute(stmt)
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
        return "fail"

    # Save to Valkey
    v_client = get_valkey_client()
    try:
        # Cache the user's mowers list
        await v_client.setex(
            valkey_user_mowers_key, 86400, json.dumps(mower_ids)
        )

        # Cache each mower's data and retrieve status in valkey
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
        # Default status to offline if Valkey call fails
        for m_data in mowers_list:
            if "status" not in m_data:
                m_data["status"] = "offline"
    finally:
        await v_client.close()

    return mowers_list
