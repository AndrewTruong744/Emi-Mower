from unittest.mock import AsyncMock, Mock

import pytest

from src.services import zenoh_credentials


@pytest.mark.asyncio
async def test_provision_zenoh_credential_configures_router_then_records_expiry(
    monkeypatch,
):
    client = Mock()
    client.configure_user_app = AsyncMock()
    record_expiry = AsyncMock()
    monkeypatch.setattr(
        zenoh_credentials, "ZenohAdminClient", Mock(return_value=client)
    )
    monkeypatch.setattr(
        zenoh_credentials, "record_zenoh_credential_expiry", record_expiry
    )
    monkeypatch.setattr(zenoh_credentials.time, "time", lambda: 100)

    await zenoh_credentials.provision_zenoh_credential(
        "user-1", ["mower-1"], "jwt", 300
    )

    client.configure_user_app.assert_awaited_once_with(
        user_id="user-1", mower_ids=["mower-1"], password="jwt"
    )
    record_expiry.assert_awaited_once_with("user-1", 400)


@pytest.mark.asyncio
async def test_remove_expired_zenoh_credentials_deletes_passwords_then_expiries(
    monkeypatch,
):
    client = Mock()
    client.delete_user_password = AsyncMock()
    remove_expiries = AsyncMock()
    monkeypatch.setattr(
        zenoh_credentials, "ZenohAdminClient", Mock(return_value=client)
    )
    monkeypatch.setattr(
        zenoh_credentials,
        "get_expired_zenoh_credential_user_ids",
        AsyncMock(return_value=["user-1", "user-2"]),
    )
    monkeypatch.setattr(
        zenoh_credentials, "remove_zenoh_credential_expiries", remove_expiries
    )

    await zenoh_credentials.remove_expired_zenoh_credentials(100)

    assert client.delete_user_password.await_count == 2
    remove_expiries.assert_awaited_once_with(["user-1", "user-2"])


@pytest.mark.asyncio
async def test_remove_expired_zenoh_credentials_retries_users_that_fail(monkeypatch):
    client = Mock()
    client.delete_user_password = AsyncMock(
        side_effect=[RuntimeError("router unavailable"), None]
    )
    remove_expiries = AsyncMock()
    monkeypatch.setattr(
        zenoh_credentials, "ZenohAdminClient", Mock(return_value=client)
    )
    monkeypatch.setattr(
        zenoh_credentials,
        "get_expired_zenoh_credential_user_ids",
        AsyncMock(return_value=["user-1", "user-2"]),
    )
    monkeypatch.setattr(
        zenoh_credentials, "remove_zenoh_credential_expiries", remove_expiries
    )

    await zenoh_credentials.remove_expired_zenoh_credentials(100)

    remove_expiries.assert_awaited_once_with(["user-2"])
