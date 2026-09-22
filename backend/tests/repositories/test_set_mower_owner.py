import uuid

import pytest
from sqlalchemy import select

from src.exceptions import MowerNotFoundError, UserNotFoundError
from src.models.mower import MowerModel
from src.repositories.set_mower_owner import set_mower_owner
from src.schemas.valkey import mower_data_key, user_mowers_key

pytestmark = pytest.mark.repository


async def test_set_mower_owner_transfers_owner_and_invalidates_related_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user("old-owner")
    await seed_user("new-owner", "new@example.test", "New")
    mower = await seed_mower(owner_id="old-owner")
    keys = [
        mower_data_key(str(mower.id)),
        user_mowers_key("old-owner"),
        user_mowers_key("new-owner"),
    ]
    await cache.mset({key: "stale" for key in keys})

    await set_mower_owner("new-owner", mower.id, db_session)

    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "new-owner"
    assert await cache.mget(keys) == [None, None, None]


async def test_set_mower_owner_assigns_unowned_mower_and_invalidates_new_owner_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user("new-owner", "new@example.test", "New")
    mower = await seed_mower(owner_id=None)
    keys = [
        mower_data_key(str(mower.id)),
        user_mowers_key("new-owner"),
    ]
    await cache.mset({key: "stale" for key in keys})

    await set_mower_owner("new-owner", mower.id, db_session)

    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "new-owner"
    assert await cache.mget(keys) == [None, None]


async def test_set_mower_owner_rejects_nonexistent_user_without_mutating_mower(
    db_session, seed_mower
):
    mower = await seed_mower(owner_id=None)

    with pytest.raises(UserNotFoundError):
        await set_mower_owner("missing-user", mower.id, db_session)

    assert (await db_session.execute(select(MowerModel.owner_id))).scalar_one() is None


async def test_set_mower_owner_rejects_nonexistent_mower(db_session, seed_user):
    await seed_user()

    with pytest.raises(MowerNotFoundError):
        await set_mower_owner(
            "user-1", uuid.UUID("00000000-0000-0000-0000-000000000001"), db_session
        )


async def test_set_mower_owner_can_unassign_a_mower(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower(owner_id="user-1")
    await cache.set(user_mowers_key("user-1"), "stale")

    await set_mower_owner(None, mower.id, db_session)

    assert (await db_session.execute(select(MowerModel.owner_id))).scalar_one() is None
    assert await cache.get(user_mowers_key("user-1")) is None
