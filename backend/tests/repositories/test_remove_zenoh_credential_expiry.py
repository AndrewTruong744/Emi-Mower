import pytest

from src.repositories.zenoh_credentials import remove_zenoh_credential_expiries
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

pytestmark = pytest.mark.repository


async def test_remove_zenoh_credential_expiries_removes_expiries(cache):
    await cache.hset(
        ZENOH_TOKEN_EXPIRY_KEY, mapping={"user-1": "1234", "user-2": "5678"}
    )

    await remove_zenoh_credential_expiries(["user-1", "user-2"])

    assert await cache.hget(ZENOH_TOKEN_EXPIRY_KEY, "user-1") is None
    assert await cache.hget(ZENOH_TOKEN_EXPIRY_KEY, "user-2") is None
