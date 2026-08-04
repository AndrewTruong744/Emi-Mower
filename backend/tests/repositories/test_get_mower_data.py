import pytest

from src.repositories.get_mower_data import get_mower_data
from src.schemas.valkey import (
    MowerDataCache,
    mower_data_key,
    mower_status_key,
    user_mowers_key,
)

pytestmark = pytest.mark.repository


async def test_get_mower_data_populates_cache_on_miss(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower(nickname="DatabaseMower")

    result = await get_mower_data("user-1", db_session)

    assert result == [
        {
            "id": str(mower.id),
            "serial_number": "serial-1",
            "nickname": "DatabaseMower",
            "owner_id": "user-1",
            "status": "offline",
        }
    ]
    assert (
        MowerDataCache.model_validate_json(
            await cache.get(mower_data_key(str(mower.id)))
        ).nickname
        == "DatabaseMower"
    )


async def test_get_mower_data_uses_complete_cache_hit(db_session, cache, seed_user):
    await seed_user()
    mower_id = "00000000-0000-0000-0000-000000000001"
    await cache.set(user_mowers_key("user-1"), f'["{mower_id}"]')
    await cache.set(
        mower_data_key(mower_id),
        MowerDataCache(
            id=mower_id,
            serial_number="cached",
            nickname="CachedMower",
            owner_id="user-1",
        ).model_dump_json(),
    )
    await cache.set(mower_status_key(mower_id), "online")

    assert (await get_mower_data("user-1", db_session))[0]["nickname"] == "CachedMower"


async def test_get_mower_data_falls_back_when_a_cached_mower_entry_is_missing(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower(nickname="DatabaseMower")
    await cache.set(user_mowers_key("user-1"), f'["{mower.id}"]')

    result = await get_mower_data("user-1", db_session)

    assert result[0]["nickname"] == "DatabaseMower"
