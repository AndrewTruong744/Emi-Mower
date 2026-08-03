import pytest

from src.repositories.zenoh_credentials import record_zenoh_credential_expiry
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

pytestmark = pytest.mark.repository


async def test_record_zenoh_credential_expiry_writes_expiry(cache):
    await record_zenoh_credential_expiry("user-1", 1234)

    assert await cache.hget(ZENOH_TOKEN_EXPIRY_KEY, "user-1") == "1234"
