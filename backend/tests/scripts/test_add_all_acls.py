from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from src.scripts import add_all_acls


@pytest.mark.asyncio
async def test_add_all_acls_configures_every_user_and_mower(monkeypatch):
    db = AsyncMock()

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

    monkeypatch.setattr(
        add_all_acls,
        "user_authorization_snapshot",
        AsyncMock(return_value=({}, ["mower-1"])),
    )
    await add_all_acls.add_all_acls()

    client.configure_user_app.assert_awaited_once_with(
        user_id="user-1", mower_ids=["mower-1"]
    )
    client.configure_mower_device.assert_awaited_once_with("mower-1")


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

    await add_all_acls.add_all_acls()

    client.configure_user_app.assert_not_awaited()
    client.configure_mower_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_all_acls_propagates_database_loading_failures(monkeypatch):
    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(add_all_acls, "AsyncSessionLocal", fake_session)
    monkeypatch.setattr(
        add_all_acls,
        "get_all_mowers_and_users",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    with pytest.raises(RuntimeError):
        await add_all_acls.add_all_acls()
