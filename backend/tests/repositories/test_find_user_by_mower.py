import pytest

from src.repositories.find_user_by_mower import find_user_by_mower
from src.schemas.valkey import mower_owner_key

pytestmark = pytest.mark.repository


async def test_find_user_by_mower_caches_database_owner(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await find_user_by_mower(mower.id, db_session) == "user-1"
    assert await cache.get(mower_owner_key(str(mower.id))) == "user-1"


async def test_find_user_by_mower_returns_cache_hit(db_session, cache):
    mower_id = "00000000-0000-0000-0000-000000000001"
    await cache.set(mower_owner_key(mower_id), "cached-owner")

    assert await find_user_by_mower(mower_id, db_session) == "cached-owner"


async def test_find_user_by_mower_returns_none_for_malformed_uuid(db_session):
    assert await find_user_by_mower("not-a-uuid", db_session) is None


async def test_find_user_by_mower_caches_unowned_mower(db_session, cache, seed_mower):
    mower = await seed_mower(owner_id=None)

    assert await find_user_by_mower(mower.id, db_session) is None
    assert await cache.get(mower_owner_key(str(mower.id))) == "dne"
