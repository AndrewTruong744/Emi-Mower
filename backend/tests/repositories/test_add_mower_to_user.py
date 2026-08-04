import pytest
from sqlalchemy import select

from src.exceptions import MowerNotFoundError, UserNotFoundError
from src.models.mower import MowerModel
from src.repositories.add_mower_to_user import add_mower_to_user
from src.schemas.valkey import mower_data_key, mower_owner_key, user_mowers_key

pytestmark = pytest.mark.repository


async def test_add_mower_to_user_transfers_owner_and_invalidates_related_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user("old-owner")
    await seed_user("new-owner", "new@example.test", "New")
    mower = await seed_mower(owner_id="old-owner")
    keys = [
        mower_data_key(str(mower.id)),
        mower_owner_key(str(mower.id)),
        user_mowers_key("old-owner"),
        user_mowers_key("new-owner"),
    ]
    await cache.mset({key: "stale" for key in keys})

    await add_mower_to_user("new-owner", str(mower.id), db_session)

    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "new-owner"
    assert await cache.mget(keys) == [None, None, None, None]


async def test_add_mower_to_user_assigns_unowned_mower_and_invalidates_new_owner_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user("new-owner", "new@example.test", "New")
    mower = await seed_mower(owner_id=None)
    keys = [
        mower_data_key(str(mower.id)),
        mower_owner_key(str(mower.id)),
        user_mowers_key("new-owner"),
    ]
    await cache.mset({key: "stale" for key in keys})

    await add_mower_to_user("new-owner", str(mower.id), db_session)

    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "new-owner"
    assert await cache.mget(keys) == [None, None, None]


async def test_add_mower_to_user_rejects_nonexistent_user_without_mutating_mower(
    db_session, seed_mower
):
    mower = await seed_mower(owner_id=None)

    with pytest.raises(UserNotFoundError):
        await add_mower_to_user("missing-user", str(mower.id), db_session)

    assert (await db_session.execute(select(MowerModel.owner_id))).scalar_one() is None


async def test_add_mower_to_user_rejects_nonexistent_mower(db_session, seed_user):
    await seed_user()

    with pytest.raises(MowerNotFoundError):
        await add_mower_to_user(
            "user-1", "00000000-0000-0000-0000-000000000001", db_session
        )


async def test_add_mower_to_user_can_unassign_a_mower(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower(owner_id="user-1")
    await cache.set(user_mowers_key("user-1"), "stale")

    await add_mower_to_user(None, str(mower.id), db_session)

    assert (await db_session.execute(select(MowerModel.owner_id))).scalar_one() is None
    assert await cache.get(user_mowers_key("user-1")) is None
