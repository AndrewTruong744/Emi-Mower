"""Stage single-mower ownership changes under the same locks used by login."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import MowerNotFoundError, OwnershipError, ValidationError
from src.models.mower import MowerModel
from src.repositories.account_switch import (
    lock_account_changes,
    user_authorization_snapshot,
)
from src.schemas.valkey import mower_data_key, user_mowers_key


async def stage_mower_ownership(
    current_owner_id: str | None,
    new_owner_id: str | None,
    mower_id: UUID,
    db: AsyncSession,
) -> dict[str, list[str]]:
    """Validate both accounts and the mower, then stage without committing."""
    owners = sorted({owner for owner in (current_owner_id, new_owner_id) if owner})
    if not owners or current_owner_id == new_owner_id:
        raise ValidationError("Choose a different recipient account")
    await lock_account_changes(owners, db)
    # A recipient must already have an app account. Never create one from an ID.
    for owner in owners:
        await user_authorization_snapshot(owner, db)
    mower = (
        await db.execute(
            select(MowerModel).where(MowerModel.id == mower_id).with_for_update()
        )
    ).scalar_one_or_none()
    if mower is None:
        raise MowerNotFoundError("No registered mower exists with this UUID")
    if mower.owner_id != current_owner_id:
        raise OwnershipError(
            "This mower already belongs to an account"
            if current_owner_id is None
            else "You do not own this mower"
        )
    if current_owner_id is None and mower.lifecycle_status != "active":
        raise ValidationError("This mower is not active and cannot be added")
    mower.owner_id = new_owner_id
    await db.flush()
    snapshots = {}
    for owner in owners:
        _, snapshots[owner] = await user_authorization_snapshot(owner, db)
    return snapshots


async def invalidate_mower_ownership(mower_id: UUID, owners: list[str]) -> None:
    """Clear both ownership projections; the database remains authoritative."""
    async with get_valkey_client() as cache:
        await cache.delete(
            mower_data_key(str(mower_id)),
            *[user_mowers_key(owner) for owner in owners],
        )
