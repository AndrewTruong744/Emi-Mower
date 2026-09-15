import pytest

from src.repositories.find_user_by_mower import find_user_by_mower
from src.schemas.valkey import MowerDataCache, mower_data_key

pytestmark = pytest.mark.repository


async def test_find_user_by_mower_delegates_to_the_shared_mower_data_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await find_user_by_mower(mower.id, db_session) == "user-1"
    assert MowerDataCache.model_validate_json(
        await cache.get(mower_data_key(str(mower.id)))
    ).owner_id == "user-1"


async def test_find_user_by_mower_returns_none_for_malformed_uuid(db_session):
    assert await find_user_by_mower("not-a-uuid", db_session) is None
