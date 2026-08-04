import pytest

from src.repositories.get_mowers_of_user import get_mowers_of_user
from src.schemas.valkey import UserMowersCache, user_mowers_key

pytestmark = pytest.mark.repository


async def test_get_mowers_of_user_populates_cache_on_miss(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await get_mowers_of_user("user-1", db_session) == [str(mower.id)]
    assert UserMowersCache.model_validate_json(
        await cache.get(user_mowers_key("user-1"))
    ).root == [str(mower.id)]


async def test_get_mowers_of_user_returns_cache_hit(db_session, cache, seed_user):
    await seed_user()
    await cache.set(
        user_mowers_key("user-1"), UserMowersCache(["cached-mower"]).model_dump_json()
    )

    assert await get_mowers_of_user("user-1", db_session) == ["cached-mower"]


async def test_get_mowers_of_user_returns_empty_list_for_unknown_user(db_session):
    assert await get_mowers_of_user("missing-user", db_session) == []
