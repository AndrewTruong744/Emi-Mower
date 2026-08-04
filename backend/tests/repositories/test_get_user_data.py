import pytest

from src.repositories.get_user_data import get_user_data
from src.exceptions import UserNotFoundError
from src.schemas.valkey import UserDataCache, user_data_key

pytestmark = pytest.mark.repository


async def test_get_user_data_reads_database_on_miss_and_populates_cache(
    db_session, cache, seed_user
):
    await seed_user(name="DatabaseName")

    result = await get_user_data("user-1", db_session)

    assert result["name"] == "DatabaseName"
    assert (
        UserDataCache.model_validate_json(await cache.get(user_data_key("user-1"))).name
        == "DatabaseName"
    )


async def test_get_user_data_returns_cache_hit(db_session, cache, seed_user):
    await seed_user(name="DatabaseName")
    await cache.set(
        user_data_key("user-1"),
        UserDataCache(
            id="user-1", email="cached@example.test", name="CachedName"
        ).model_dump_json(),
    )

    assert (await get_user_data("user-1", db_session))["name"] == "CachedName"


async def test_get_user_data_raises_for_missing_user(db_session):
    with pytest.raises(UserNotFoundError):
        await get_user_data("missing-user", db_session)


async def test_get_user_data_recovers_from_malformed_cache(
    db_session, cache, seed_user
):
    await seed_user(name="DatabaseName")
    await cache.set(user_data_key("user-1"), "not-json")

    assert (await get_user_data("user-1", db_session))["name"] == "DatabaseName"
