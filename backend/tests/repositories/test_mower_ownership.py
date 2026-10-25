"""Authoritative claim, removal and transfer against disposable SQL/cache."""

import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.config.database import AsyncSessionLocal
from src.exceptions import (
    MowerNotFoundError,
    OwnershipError,
    UserNotFoundError,
    ValidationError,
)
from src.models.mower import MowerModel
from src.schemas.valkey import mower_data_key, user_mowers_key
from src.services import mower as service

pytestmark = pytest.mark.repository


@pytest.fixture
def admin(monkeypatch):
    client = Mock(configure_user_app=AsyncMock(), revoke_user=AsyncMock())
    monkeypatch.setattr(service, "ZenohAdminClient", lambda: client)
    return client


async def owner(db, mower_id):
    return (
        await db.execute(select(MowerModel.owner_id).where(MowerModel.id == mower_id))
    ).scalar_one()


async def test_claim_requires_a_valid_registered_unassigned_mower(
    db_session, seed_user, seed_mower, admin
):
    await seed_user()
    await seed_user("other", "other@example.test")
    with pytest.raises(ValidationError, match="UUID"):
        await service.update_mower_ownership_service(
            None, "user-1", "garbage", db_session
        )
    with pytest.raises(MowerNotFoundError):
        await service.update_mower_ownership_service(
            None, "user-1", str(uuid4()), db_session
        )
    assigned = await seed_mower(owner_id="other")
    assigned_id = assigned.id
    with pytest.raises(OwnershipError):
        await service.update_mower_ownership_service(
            None, "user-1", str(assigned_id), db_session
        )
    assert await owner(db_session, assigned_id) == "other"
    admin.configure_user_app.assert_not_awaited()
    free = await seed_mower(owner_id=None)
    free_id = free.id
    await service.update_mower_ownership_service(
        None, "user-1", str(free_id), db_session
    )
    assert await owner(db_session, free_id) == "user-1"
    admin.configure_user_app.assert_awaited_once_with("user-1", [str(free_id)])


@pytest.mark.parametrize("destination", [None, "recipient"])
async def test_remove_or_transfer_preserves_other_mowers_and_updates_both_scopes(
    db_session, seed_user, seed_mower, cache, admin, destination
):
    await seed_user()
    await seed_user("recipient", "recipient@example.test")
    moved = await seed_mower()
    retained = await seed_mower()
    received = await seed_mower(owner_id="recipient")
    moved_id, retained_id, received_id = moved.id, retained.id, received.id
    keys = [
        mower_data_key(str(moved_id)),
        user_mowers_key("user-1"),
        user_mowers_key("recipient"),
    ]
    await cache.mset({key: "obsolete" for key in keys})
    await service.update_mower_ownership_service(
        "user-1", destination, str(moved_id), db_session
    )
    assert await owner(db_session, moved_id) == destination
    assert await owner(db_session, retained_id) == "user-1"
    assert await owner(db_session, received_id) == "recipient"
    assert admin.configure_user_app.call_args_list[0].args == (
        "user-1",
        [str(retained_id)],
    )
    if destination:
        assert set(admin.configure_user_app.call_args_list[1].args[1]) == {
            str(moved_id),
            str(received_id),
        }
    assert await cache.get(keys[0]) is None
    assert await cache.get(keys[1]) is None
    if destination:
        assert await cache.get(keys[2]) is None
    admin.revoke_user.assert_not_awaited()


async def test_cannot_remove_or_transfer_another_accounts_mower_or_to_missing_user(
    db_session, seed_user, seed_mower, admin
):
    await seed_user()
    await seed_user("recipient", "recipient@example.test")
    mower = await seed_mower()
    mower_id = mower.id
    for current, destination, error in [
        ("recipient", None, OwnershipError),
        ("recipient", "user-1", OwnershipError),
        ("user-1", "missing", UserNotFoundError),
        ("user-1", "user-1", ValidationError),
    ]:
        with pytest.raises(error):
            await service.update_mower_ownership_service(
                current, destination, str(mower_id), db_session
            )
        assert await owner(db_session, mower_id) == "user-1"
    admin.configure_user_app.assert_not_awaited()


async def test_revocation_failure_rolls_back_database_ownership(
    db_session, seed_user, seed_mower, admin
):
    await seed_user()
    await seed_user("recipient", "recipient@example.test")
    mower = await seed_mower()
    mower_id = mower.id
    admin.configure_user_app.side_effect = [RuntimeError("unreachable"), None]
    with pytest.raises(RuntimeError):
        await service.update_mower_ownership_service(
            "user-1", "recipient", str(mower_id), db_session
        )
    assert await owner(db_session, mower_id) == "user-1"
    assert admin.configure_user_app.call_args_list[-1].args == (
        "user-1",
        [str(mower_id)],
    )


async def test_inactive_mower_cannot_be_claimed(
    db_session, seed_user, seed_mower, admin
):
    await seed_user()
    mower = await seed_mower(owner_id=None)
    mower.lifecycle_status = "decommissioned"
    mower_id = mower.id
    await db_session.commit()
    with pytest.raises(ValidationError, match="not active"):
        await service.update_mower_ownership_service(
            None, "user-1", str(mower_id), db_session
        )
    assert await owner(db_session, mower_id) is None


async def test_concurrent_claims_assign_exactly_one_owner(
    db_session, seed_user, seed_mower, admin
):
    await seed_user()
    await seed_user("recipient", "recipient@example.test")
    mower = await seed_mower(owner_id=None)
    mower_id = mower.id

    async def claim(user_id):
        async with AsyncSessionLocal() as db:
            await service.update_mower_ownership_service(
                None, user_id, str(mower_id), db
            )

    results = await asyncio.gather(
        claim("user-1"), claim("recipient"), return_exceptions=True
    )
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, OwnershipError) for result in results) == 1
    winner = "user-1" if results[0] is None else "recipient"
    assert await owner(db_session, mower_id) == winner
    admin.configure_user_app.assert_awaited_once_with(winner, [str(mower_id)])
