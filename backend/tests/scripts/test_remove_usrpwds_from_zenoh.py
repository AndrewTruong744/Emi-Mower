from unittest.mock import AsyncMock, Mock

import pytest

from src.scripts import remove_usrpwds_from_zenoh as checker


@pytest.mark.asyncio
async def test_remove_expired_usrpwds_deletes_password_and_expiry(monkeypatch):
    client = Mock()
    client.delete_user_password = AsyncMock()
    monkeypatch.setattr(checker, "ZenohAdminClient", Mock(return_value=client))
    monkeypatch.setattr(checker.time, "time", lambda: 100)
    monkeypatch.setattr(
        checker,
        "get_expired_zenoh_credential_user_ids",
        AsyncMock(return_value=["user-1", "user-2"]),
    )
    remove = AsyncMock()
    monkeypatch.setattr(checker, "remove_zenoh_credential_expiry", remove)

    await checker.remove_expired_usrpwds()

    assert client.delete_user_password.await_count == 2
    assert remove.await_count == 2


@pytest.mark.asyncio
async def test_remove_expired_usrpwds_is_noop_when_no_credentials_are_expired(
    monkeypatch,
):
    client = Mock()
    client.delete_user_password = AsyncMock()
    monkeypatch.setattr(checker, "ZenohAdminClient", Mock(return_value=client))
    monkeypatch.setattr(
        checker,
        "get_expired_zenoh_credential_user_ids",
        AsyncMock(return_value=[]),
    )
    remove = AsyncMock()
    monkeypatch.setattr(checker, "remove_zenoh_credential_expiry", remove)

    await checker.remove_expired_usrpwds()

    client.delete_user_password.assert_not_awaited()
    remove.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_expired_usrpwds_continues_after_one_user_fails(monkeypatch):
    client = Mock()
    client.delete_user_password = AsyncMock(
        side_effect=[RuntimeError("router unavailable"), None]
    )
    monkeypatch.setattr(checker, "ZenohAdminClient", Mock(return_value=client))
    monkeypatch.setattr(
        checker,
        "get_expired_zenoh_credential_user_ids",
        AsyncMock(return_value=["user-1", "user-2"]),
    )
    remove = AsyncMock()
    monkeypatch.setattr(checker, "remove_zenoh_credential_expiry", remove)

    await checker.remove_expired_usrpwds()

    assert remove.await_count == 1
    remove.assert_awaited_once_with("user-2")


@pytest.mark.asyncio
async def test_run_checker_closes_http_client_when_stopped(monkeypatch):
    monkeypatch.setattr(checker, "remove_expired_usrpwds", AsyncMock())
    close = AsyncMock()
    monkeypatch.setattr(checker, "close_http_client", close)

    async def stop(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(checker.asyncio, "sleep", stop)

    with pytest.raises(KeyboardInterrupt):
        await checker.run_checker()
    close.assert_awaited_once()
