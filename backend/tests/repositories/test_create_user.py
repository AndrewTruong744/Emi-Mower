import pytest

from src.repositories.create_user import create_user
from src.schemas.valkey import VALKEY_CACHE_TTL_SECONDS, UserDataCache, user_data_key

pytestmark = pytest.mark.repository


async def test_create_user_persists_and_caches_user(db_session, cache):
    result = await create_user("user-1", "one@example.test", "One", db_session)

    assert result["id"] == "user-1"
    cached = UserDataCache.model_validate_json(await cache.get(user_data_key("user-1")))
    assert cached.email == "one@example.test"
    assert 0 < await cache.ttl(user_data_key("user-1")) <= VALKEY_CACHE_TTL_SECONDS
