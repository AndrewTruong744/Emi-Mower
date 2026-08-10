from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from src.scripts import add_all_acls


@pytest.mark.asyncio
async def test_add_all_acls_configures_every_user_and_mower(monkeypatch):
    db = object()

    @asynccontextmanager
    async def fake_session():
        yield db

    client = Mock()
    client.configure_user_app = AsyncMock()
    client.configure_mower_device = AsyncMock()
    monkeypatch.setattr(add_all_acls, "AsyncSessionLocal", fake_session)
    monkeypatch.setattr(
        add_all_acls,
        "get_all_mowers_and_users",
        AsyncMock(
            return_value={
                "users": [{"user_id": "user-1", "mower_ids": ["mower-1"]}],
                "mowers": [{"mower_id": "mower-1", "owner_id": "user-1"}],
            }
        ),
    )
    monkeypatch.setattr(add_all_acls, "ZenohAdminClient", Mock(return_value=client))
    close = AsyncMock()
    monkeypatch.setattr(add_all_acls, "close_http_client", close)

    await add_all_acls.add_all_acls()

    client.configure_user_app.assert_awaited_once_with(
        user_id="user-1", mower_ids=["mower-1"]
    )
    client.configure_mower_device.assert_awaited_once_with("mower-1")
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_all_acls_is_noop_when_database_has_no_users_or_mowers(monkeypatch):
    @asynccontextmanager
    async def fake_session():
        yield object()

    client = Mock()
    client.configure_user_app = AsyncMock()
    client.configure_mower_device = AsyncMock()
    monkeypatch.setattr(add_all_acls, "AsyncSessionLocal", fake_session)
    monkeypatch.setattr(
        add_all_acls,
        "get_all_mowers_and_users",
        AsyncMock(return_value={"users": [], "mowers": []}),
    )
    monkeypatch.setattr(add_all_acls, "ZenohAdminClient", Mock(return_value=client))
    close = AsyncMock()
    monkeypatch.setattr(add_all_acls, "close_http_client", close)

    await add_all_acls.add_all_acls()

    client.configure_user_app.assert_not_awaited()
    client.configure_mower_device.assert_not_awaited()
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_all_acls_closes_http_client_when_database_loading_fails(monkeypatch):
    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(add_all_acls, "AsyncSessionLocal", fake_session)
    monkeypatch.setattr(
        add_all_acls,
        "get_all_mowers_and_users",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )
    close = AsyncMock()
    monkeypatch.setattr(add_all_acls, "close_http_client", close)

    with pytest.raises(RuntimeError):
        await add_all_acls.add_all_acls()
    close.assert_awaited_once()
