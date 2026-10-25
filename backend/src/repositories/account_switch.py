"""Transactional Google-account ownership changes and authoritative login reads."""

import logging

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import UserNotFoundError, ValidationError
from src.models.mower import MowerModel
from src.models.user import UserModel
from src.schemas.valkey import (
    ZENOH_TOKEN_EXPIRY_KEY,
    mower_data_key,
    user_data_key,
    user_mowers_key,
)

logger = logging.getLogger(__name__)


async def user_authorization_snapshot(user_id: str, db: AsyncSession):
    """Lock the account until login finishes; never grant from cached ownership."""
    user = (
        await db.execute(
            select(UserModel).where(UserModel.id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if user is None:
        raise UserNotFoundError("User account was not found")
    mowers = (
        (await db.execute(select(MowerModel.id).where(MowerModel.owner_id == user_id)))
        .scalars()
        .all()
    )
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }, [str(value) for value in mowers]


async def stage_account_switch(
    source_id: str, target_id: str, email: str, db: AsyncSession
) -> list[str]:
    """Stage the entire transfer. Caller narrows ACLs before committing.

    Account locks serialize this operation against login's policy publication.
    Mower UUIDs, certificates and telemetry stay attached to the same mower rows.
    """
    users = (
        (
            await db.execute(
                select(UserModel)
                .where(UserModel.id.in_([source_id, target_id]))
                .order_by(UserModel.id)
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    accounts = {user.id: user for user in users}
    source = accounts.get(source_id)
    if source is None:
        raise UserNotFoundError("The original account no longer exists")
    email_owner = (
        await db.execute(select(UserModel.id).where(UserModel.email == email))
    ).scalar_one_or_none()
    if email_owner is not None and email_owner not in (source_id, target_id):
        raise ValidationError("The email address is already in use")
    mowers = (
        (
            await db.execute(
                select(MowerModel.id)
                .where(MowerModel.owner_id == source_id)
                .order_by(MowerModel.id)
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    profile_name, created_at = source.name, source.created_at
    # SET NULL happens only inside this transaction; ownership is restored below
    # before commit. Removing the source first also frees its unique email.
    await db.execute(delete(UserModel).where(UserModel.id == source_id))
    target = accounts.get(target_id)
    if target is None:
        db.add(
            UserModel(
                id=target_id, email=email, name=profile_name, created_at=created_at
            )
        )
    else:
        target.email = email
    await db.flush()
    if mowers:
        await db.execute(
            update(MowerModel)
            .where(MowerModel.id.in_(mowers))
            .values(owner_id=target_id)
        )
    return [str(value) for value in mowers]


async def invalidate_account_switch_cache(
    source_id: str, target_id: str, mower_ids: list[str]
) -> None:
    """Scrub old profile/ownership entries and any retired credential registry."""
    async with get_valkey_client() as cache:
        pipeline = cache.pipeline()
        pipeline.delete(
            user_data_key(source_id),
            user_mowers_key(source_id),
            user_data_key(target_id),
            user_mowers_key(target_id),
            *[mower_data_key(value) for value in mower_ids],
        )
        pipeline.hdel(ZENOH_TOKEN_EXPIRY_KEY, source_id)
        await pipeline.execute()


async def lock_account_changes(user_ids: list[str], db: AsyncSession) -> None:
    """Use the same lock order for single-mower ownership and account transfers."""
    if user_ids:
        await db.execute(
            select(UserModel.id)
            .where(UserModel.id.in_(user_ids))
            .order_by(UserModel.id)
            .with_for_update()
        )
