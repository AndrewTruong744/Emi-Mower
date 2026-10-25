import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import (
    ExternalServiceError,
    MowerNotFoundError,
    OwnershipError,
    ValidationError,
)
from src.repositories import (
    add_telemetry_to_cache,
    get_mower_data_for_user,
    get_telemetry_history,
    update_mower_name,
    verify_ownership,
)
from src.repositories.account_switch import user_authorization_snapshot
from src.repositories.get_telemetry_history import TELEMETRY_PAGE_SIZE
from src.repositories.mower_ownership import (
    invalidate_mower_ownership,
    stage_mower_ownership,
)
from src.zenoh.generated import TelemetryRecord

logger = logging.getLogger("services.mower_service")


def mower_route_params(key_expr: str, pattern: str) -> tuple[str, ...]:
    """Match a concrete mower route and return its non-empty wildcard values."""
    actual = str(key_expr).split("/")
    expected = pattern.split("/")
    if len(actual) != len(expected) or any(
        not segment or (template != "*" and segment != template)
        for segment, template in zip(actual, expected, strict=True)
    ):
        raise ValidationError("Invalid mower query path")
    return tuple(
        segment
        for segment, template in zip(actual, expected, strict=True)
        if template == "*"
    )


def _parse_mower_id(mower_id: str) -> uuid.UUID:
    """Validate a transport mower ID before passing it to repositories."""
    try:
        return uuid.UUID(mower_id)
    except (TypeError, ValueError) as error:
        raise ValidationError("Mower ID must be a UUID") from error


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
) -> dict:
    """Read one authorized, cursor-paged newest-first 60-point graph page."""
    mower_uuid = _parse_mower_id(mower_id)
    if not await verify_ownership(user_id, mower_uuid, db):
        raise OwnershipError(f"User {user_id} does not own mower {mower_id}")

    total, points, next_cursor = await get_telemetry_history(
        mower_uuid, telemetry_type, cursor, db
    )
    return {
        "telemetry_type": telemetry_type,
        "limit": TELEMETRY_PAGE_SIZE,
        "total": total,
        "next_cursor": next_cursor,
        "points": [
            (timestamp, float(value))
            for timestamp, value, _ in points
            if value is not None
        ],
    }


async def get_mower_data_service(user_id: str, mower_id: str, db: AsyncSession) -> dict:
    """
    Service to retrieve a specific mower's data for a user.
    Calls get_mower_data_for_user to fetch all mowers owned by the user
    and returns the one matching mower_id.
    Raises MowerNotFoundError if mower does not exist or user does not own it.
    """
    logger.info(f"get_mower_data_service called for user {user_id}, mower {mower_id}")
    mower_uuid = _parse_mower_id(mower_id)

    mowers = await get_mower_data_for_user(user_id, db=db)

    # Find the specific mower by ID (which verifies ownership implicitly)
    for mower in mowers:
        if mower.get("id") == str(mower_uuid):
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
    mower_uuid = _parse_mower_id(mower_id)

    # 1. Verify alphanumeric format
    if not new_name.isalnum():
        logger.warning(f"Nickname update rejected: '{new_name}' is not alphanumeric.")
        raise ValidationError(f"Nickname '{new_name}' is not alphanumeric")

    # 2. Verify ownership
    is_owner = await verify_ownership(user_id, mower_uuid, db=db)
    if not is_owner:
        logger.warning(
            "Ownership verification failed: User %s does not own mower %s",
            user_id,
            mower_id,
        )
        raise OwnershipError(f"User {user_id} does not own mower {mower_id}")

    # 3. Call repository to update DB and cache
    await update_mower_name(mower_uuid, new_name, db=db)


async def update_mower_ownership_service(
    current_owner_id: str | None,
    new_owner_id: str | None,
    mower_id: str,
    db: AsyncSession,
) -> None:
    """
    Service to update/transfer mower ownership.
    Checks the actual owner first. An unowned mower can be assigned; an owned
    mower can be transferred only by its current owner.
    Raises OwnershipError, MowerNotFoundError, or RepositoryError.
    """
    logger.info(
        "update_mower_ownership_service: current=%s, new=%s, mower=%s",
        current_owner_id,
        new_owner_id,
        mower_id,
    )
    mower_uuid = _parse_mower_id(mower_id)

    admin = ZenohAdminClient()
    narrowed = False
    committed = False
    owners = sorted({owner for owner in (current_owner_id, new_owner_id) if owner})
    try:
        policies = await stage_mower_ownership(
            current_owner_id, new_owner_id, mower_uuid, db
        )
        if current_owner_id:
            # Revoke only this mower before ownership changes become visible.
            # Keep user/** replies and unrelated mower traffic on live sessions.
            narrowed = True
            await admin.configure_user_app(current_owner_id, policies[current_owner_id])
        await invalidate_mower_ownership(mower_uuid, owners)
        await db.commit()
        committed = True
        # Clear entries that concurrent cache readers could have repopulated
        # from the previous committed database state.
        await invalidate_mower_ownership(mower_uuid, owners)
        if new_owner_id:
            # Publish grants only after commit, under a fresh account lock.
            # Concurrent login/transfer must never restore an obsolete snapshot.
            _, mower_ids = await user_authorization_snapshot(new_owner_id, db)
            await admin.configure_user_app(new_owner_id, mower_ids)
            await db.commit()
    except Exception as error:
        await db.rollback()
        if committed:
            raise ExternalServiceError(
                "Ownership was saved, but access refresh failed. "
                "Refresh your fleet or sign in again."
            ) from error
        if narrowed and current_owner_id:
            # Restore from SQL after rollback, never from an earlier cached list.
            try:
                _, mower_ids = await user_authorization_snapshot(current_owner_id, db)
                await admin.configure_user_app(current_owner_id, mower_ids)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception(
                    "Ownership rollback needs a fresh user login to restore permissions"
                )
        raise
