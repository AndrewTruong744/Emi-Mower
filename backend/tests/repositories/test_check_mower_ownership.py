import pytest

from src.repositories.check_mower_ownership import check_mower_ownership
from src.schemas.valkey import mower_owner_key

pytestmark = pytest.mark.repository


async def test_check_mower_ownership_caches_database_owner(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await check_mower_ownership(str(mower.id), db_session) == "user-1"
    assert await cache.get(mower_owner_key(str(mower.id))) == "user-1"


async def test_check_mower_ownership_returns_cached_negative_value(db_session, cache):
    mower_id = "00000000-0000-0000-0000-000000000001"
    await cache.set(mower_owner_key(mower_id), "dne")

    assert await check_mower_ownership(mower_id, db_session) is None


async def test_check_mower_ownership_returns_none_for_malformed_uuid(db_session):
    assert await check_mower_ownership("not-a-uuid", db_session) is None


async def test_check_mower_ownership_treats_empty_cache_value_as_unowned(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()
    await cache.set(mower_owner_key(str(mower.id)), "")

    assert await check_mower_ownership(str(mower.id), db_session) is None
