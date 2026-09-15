import pytest

from src.repositories.check_mower_ownership import check_mower_ownership
from src.schemas.valkey import MowerDataCache, mower_data_key

pytestmark = pytest.mark.repository


async def test_check_mower_ownership_uses_the_shared_mower_data_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await check_mower_ownership(str(mower.id), db_session) == "user-1"
    cached = MowerDataCache.model_validate_json(
        await cache.get(mower_data_key(str(mower.id)))
    )
    assert cached.owner_id == "user-1"
    assert cached.nickname == mower.nickname


async def test_check_mower_ownership_reads_an_unowned_mower_from_shared_cache(
    db_session, cache
):
    mower_id = "00000000-0000-0000-0000-000000000001"
    await cache.set(
        mower_data_key(mower_id),
        MowerDataCache(
            id=mower_id,
            serial_number="cached",
            nickname="Cached mower",
            owner_id=None,
        ).model_dump_json(),
    )

    assert await check_mower_ownership(mower_id, db_session) is None


async def test_check_mower_ownership_returns_none_for_malformed_uuid(db_session):
    assert await check_mower_ownership("not-a-uuid", db_session) is None
