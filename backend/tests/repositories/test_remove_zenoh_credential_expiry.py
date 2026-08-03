import pytest

from src.repositories.zenoh_credentials import remove_zenoh_credential_expiry
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

pytestmark = pytest.mark.repository


async def test_remove_zenoh_credential_expiry_removes_expiry(cache):
    await cache.hset(ZENOH_TOKEN_EXPIRY_KEY, mapping={"user-1": "1234"})

    await remove_zenoh_credential_expiry("user-1")

    assert await cache.hget(ZENOH_TOKEN_EXPIRY_KEY, "user-1") is None
