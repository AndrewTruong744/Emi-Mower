import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerModel
from src.models.user import UserModel
from src.schemas.valkey import (
    VALKEY_CACHE_TTL_SECONDS,
    MowerOwnerCache,
    UserMowersCache,
    mower_owner_key,
    user_mowers_key,
)

logger = logging.getLogger("repositories.get_all_mowers_and_users")


async def get_all_mowers_and_users(db: AsyncSession) -> dict[str, list[dict]]:
    """Return all users and mowers with their ownership relationships.

    The result is shaped for the later Zenoh ACL setup:

    .. code-block:: python

        {
            "users": [{"user_id": "...", "mower_ids": ["..."]}],
            "mowers": [{"mower_id": "...", "owner_id": "..." | None}],
        }

    Users without mowers and unassigned mowers are included.  The database is
    the source of truth for this full-dataset operation; successful results
    also warm the existing per-user and per-mower Valkey entries used by the
    other repositories.

    Raises:
        RepositoryError: If either database query fails.
    """
    try:
        users_result = await db.execute(select(UserModel.id).order_by(UserModel.id))
        user_ids = [str(user_id) for user_id in users_result.scalars().all()]

        mowers_result = await db.execute(
            select(MowerModel.id, MowerModel.owner_id).order_by(MowerModel.id)
        )
        mower_rows = mowers_result.all()
    except Exception as db_err:
        logger.error(
            "Failed to query all users and mowers from Postgres: %s",
            db_err,
            exc_info=True,
        )
        raise RepositoryError("Failed to query all users and mowers") from db_err

    mowers = [
        {
            "mower_id": str(mower_id),
            "owner_id": str(owner_id) if owner_id is not None else None,
        }
        for mower_id, owner_id in mower_rows
    ]

    mowers_by_user = {user_id: [] for user_id in user_ids}
    for mower in mowers:
        owner_id = mower["owner_id"]
        if owner_id is not None:
            mowers_by_user.setdefault(owner_id, []).append(mower["mower_id"])

    users = [
        {"user_id": user_id, "mower_ids": mowers_by_user[user_id]}
        for user_id in user_ids
    ]

    # Warm the cache entries described by src/schemas/valkey.py.  Cache errors
    # must not prevent ACL setup from using the database result.
    try:
        async with get_valkey_client() as v_client:
            pipeline = v_client.pipeline()

            for user in users:
                pipeline.setex(
                    user_mowers_key(user["user_id"]),
                    VALKEY_CACHE_TTL_SECONDS,
                    UserMowersCache(user["mower_ids"]).model_dump_json(),
                )

            for mower in mowers:
                pipeline.setex(
                    mower_owner_key(mower["mower_id"]),
                    VALKEY_CACHE_TTL_SECONDS,
                    MowerOwnerCache(
                        mower["owner_id"] if mower["owner_id"] is not None else "dne"
                    ).root,
                )

            await pipeline.execute()
    except Exception as valkey_err:
        logger.warning(
            "Failed to warm Valkey while loading all users and mowers: %s",
            valkey_err,
        )

    return {"users": users, "mowers": mowers}
