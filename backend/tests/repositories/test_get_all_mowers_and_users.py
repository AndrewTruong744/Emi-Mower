import pytest

from src.repositories.get_all_mowers_and_users import get_all_mowers_and_users
from src.schemas.valkey import UserMowersCache, mower_owner_key, user_mowers_key

pytestmark = pytest.mark.repository


async def test_get_all_mowers_and_users_returns_relationships_and_warms_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user("user-1")
    await seed_user("user-2", "two@example.test", "Two")
    mower = await seed_mower(owner_id="user-1")

    result = await get_all_mowers_and_users(db_session)

    assert result == {
        "users": [
            {"user_id": "user-1", "mower_ids": [str(mower.id)]},
            {"user_id": "user-2", "mower_ids": []},
        ],
        "mowers": [{"mower_id": str(mower.id), "owner_id": "user-1"}],
    }
    assert UserMowersCache.model_validate_json(
        await cache.get(user_mowers_key("user-1"))
    ).root == [str(mower.id)]
    assert await cache.get(mower_owner_key(str(mower.id))) == "user-1"
