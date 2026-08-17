import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import (
    MowerNotFoundError,
    OwnershipError,
    ValidationError,
)
from src.repositories import (
    add_mower_to_user,
    add_telemetry_to_cache,
    check_mower_ownership,
    get_mower_data,
    get_telemetry_history,
    update_mower_name,
    verify_ownership,
)
from src.zenoh.generated import (
    TelemetryHistoryPoint,
    TelemetryHistoryResponse,
    TelemetryRecord,
)

logger = logging.getLogger("services.mower_service")


async def add_telemetry_data_service(
    telemetry_data: list[TelemetryRecord],
) -> None:
    """Buffer mower telemetry in Valkey for asynchronous database upload."""
    await add_telemetry_to_cache(telemetry_data)


async def get_telemetry_history_service(
    user_id: str,
    mower_id: str,
    telemetry_type: str,
    cursor: str | None,
    db: AsyncSession,
) -> TelemetryHistoryResponse:
    """Read one authorized, cursor-paged newest-first 60-point graph page."""
    if not await verify_ownership(user_id, mower_id, db):
        raise OwnershipError(f"User {user_id} does not own mower {mower_id}")

    total, points, next_cursor = await get_telemetry_history(
        mower_id, telemetry_type, cursor, db
    )
    return TelemetryHistoryResponse(
        telemetry_type=telemetry_type,
        limit=60,
        total=total,
        has_more=next_cursor is not None,
        next_cursor=next_cursor,
        points=[
            TelemetryHistoryPoint(timestamp=timestamp, value=float(value))
            for timestamp, value, _ in points
            if value is not None
        ],
    )


async def get_mower_data_service(user_id: str, mower_id: str, db: AsyncSession) -> dict:
    """
    Service to retrieve a specific mower's data for a user.
    Calls get_mower_data to fetch all mowers owned by the user
    and returns the one matching mower_id.
    Raises MowerNotFoundError if mower does not exist or user does not own it.
    """
    logger.info(f"get_mower_data_service called for user {user_id}, mower {mower_id}")

    mowers = await get_mower_data(user_id, db=db)

    # Find the specific mower by ID (which verifies ownership implicitly)
    for mower in mowers:
        if mower.get("id") == mower_id:
            return mower

    logger.warning(
        f"User {user_id} does not own mower {mower_id} or mower does not exist"
    )
    raise MowerNotFoundError(
        f"Mower '{mower_id}' not found or not owned by user '{user_id}'"
    )


async def update_mower_name_service(
    user_id: str, mower_id: str, new_name: str, db: AsyncSession
) -> None:
    """
    Service to update the nickname of a mower.
    First verifies ownership, then checks that the new name is alphanumeric,
    and finally calls update_mower_name repository.
    Raises ValidationError, OwnershipError, MowerNotFoundError, or RepositoryError.
    """
    logger.info(
        "update_mower_name_service called for user %s, mower %s, name %s",
        user_id,
        mower_id,
        new_name,
    )

    # 1. Verify alphanumeric format
    if not new_name.isalnum():
        logger.warning(f"Nickname update rejected: '{new_name}' is not alphanumeric.")
        raise ValidationError(f"Nickname '{new_name}' is not alphanumeric")

    # 2. Verify ownership
    is_owner = await verify_ownership(user_id, mower_id, db=db)
    if not is_owner:
        logger.warning(
            "Ownership verification failed: User %s does not own mower %s",
            user_id,
            mower_id,
        )
        raise OwnershipError(f"User {user_id} does not own mower {mower_id}")

    # 3. Call repository to update DB and cache
    await update_mower_name(mower_id, new_name, db=db)


async def update_mower_ownership_service(
    current_owner_id: str | None,
    new_owner_id: str | None,
    mower_id: str,
    db: AsyncSession,
) -> None:
    """
    Service to update/transfer mower ownership.
    Checks the actual owner first. If none exists, adds new_owner_id.
    If an owner exists, verifies it matches current_owner_id before transferring.
    Raises OwnershipError, MowerNotFoundError, or RepositoryError.
    """
    logger.info(
        "update_mower_ownership_service: current=%s, new=%s, mower=%s",
        current_owner_id,
        new_owner_id,
        mower_id,
    )

    actual_owner = await check_mower_ownership(mower_id, db=db)

    # If there is no owner, automatically add new_owner_id
    if actual_owner is None:
        logger.info(
            "Mower %s has no current owner. Assigning to: %s",
            mower_id,
            new_owner_id,
        )
        await add_mower_to_user(new_owner_id, mower_id, db=db)
        return

    # If there is an owner, verify current_owner_id matches actual_owner
    if current_owner_id != actual_owner:
        logger.warning(
            "Transfer rejected: specified owner %s != actual %s",
            current_owner_id,
            actual_owner,
        )
        raise OwnershipError(
            f"Current user {current_owner_id} is not actual owner {actual_owner}"
        )

    logger.info(
        "Transferring mower %s ownership from %s to: %s",
        mower_id,
        current_owner_id,
        new_owner_id,
    )
    await add_mower_to_user(new_owner_id, mower_id, db=db)
