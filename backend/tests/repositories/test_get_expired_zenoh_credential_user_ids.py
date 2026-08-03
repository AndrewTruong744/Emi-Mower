import pytest

from src.repositories.zenoh_credentials import get_expired_zenoh_credential_user_ids
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

pytestmark = pytest.mark.repository


async def test_get_expired_zenoh_credential_user_ids_filters_due_and_invalid_records(
    cache,
):
    await cache.hset(
        ZENOH_TOKEN_EXPIRY_KEY,
        mapping={"due": "100", "future": "101", "invalid": "not-a-time"},
    )

    assert await get_expired_zenoh_credential_user_ids(100) == ["due"]
