from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from src.config import __all__ as config_exports
from src.config import database, http_client, valkey_client
from src.config.settings import Settings
from src.config.zenoh import get_zenoh_config


def test_http_client_is_lazily_initialized_and_reused(monkeypatch):
    monkeypatch.setattr(http_client, "_http_client", None)

    first = http_client.get_http_client()
    second = http_client.get_http_client()

    assert first is second
    assert not first.is_closed


async def test_close_http_client_is_idempotent(monkeypatch):
    client = Mock()
    client.is_closed = False
    client.aclose = AsyncMock()
    monkeypatch.setattr(http_client, "_http_client", client)

    await http_client.close_http_client()
    await http_client.close_http_client()

    client.aclose.assert_awaited_once()
    assert http_client._http_client is None


def test_settings_builds_database_and_valkey_urls():
    config = Settings()
    config.POSTGRES_USER = "db-user"
    config.POSTGRES_PASSWORD = "db-password"
    config.POSTGRES_HOST = "db.example.test"
    config.POSTGRES_PORT = "55432"
    config.POSTGRES_DB = "application"
    config.VALKEY_HOST = "cache.example.test"
    config.VALKEY_PORT = 16379
    config.VALKEY_DB = 4
    config.VALKEY_PASSWORD = "cache-password"

    assert config.DATABASE_URL_ASYNC == (
        "postgresql+asyncpg://db-user:db-password@db.example.test:55432/application"
    )
    assert config.DATABASE_URL_SYNC == (
        "postgresql://db-user:db-password@db.example.test:55432/application"
    )
    assert config.VALKEY_URL == "redis://:cache-password@cache.example.test:16379/4"


def test_settings_builds_cloudflare_urls_from_account_id():
    config = Settings()
    config.CLOUDFLARE_ACCOUNT_ID = "account-123"

    assert config.CF_API_URL.endswith("/accounts/account-123/calls/apps")
    assert config.CF_RTC_URL.endswith("/apps/account-123")


def test_config_package_exports_public_dependencies():
    assert "get_db" in config_exports
    assert "get_valkey_client" in config_exports
    assert "ZenohAdminClient" in config_exports


async def test_get_valkey_closes_request_client(monkeypatch):
    client = Mock()
    client.close = AsyncMock()
    monkeypatch.setattr(valkey_client, "get_valkey_client", Mock(return_value=client))

    yielded = [item async for item in valkey_client.get_valkey()]

    assert yielded == [client]
    client.close.assert_awaited_once()


async def test_close_valkey_pool_disconnects_shared_pool(monkeypatch):
    disconnect = AsyncMock()
    monkeypatch.setattr(valkey_client.pool, "disconnect", disconnect)

    await valkey_client.close_valkey_pool()

    disconnect.assert_awaited_once()


async def test_get_db_rolls_back_when_consumer_raises(monkeypatch):
    session = Mock()
    session.rollback = AsyncMock()

    @asynccontextmanager
    async def fake_session():
        yield session

    monkeypatch.setattr(database, "AsyncSessionLocal", fake_session)
    dependency = database.get_db()
    yielded = await dependency.__anext__()
    assert yielded is session

    with pytest.raises(RuntimeError):
        await dependency.athrow(RuntimeError("request failed"))
    session.rollback.assert_awaited_once()


def test_get_zenoh_config_requires_all_certificates(monkeypatch, tmp_path):
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "server.crt"
    key = tmp_path / "server.key"
    ca.write_text("ca")
    cert.write_text("cert")
    key.write_text("key")
    monkeypatch.setattr("src.config.zenoh.settings.ZENOH_CA_CERT", str(ca))
    monkeypatch.setattr("src.config.zenoh.settings.ZENOH_FASTAPI_CERT", str(cert))
    monkeypatch.setattr("src.config.zenoh.settings.ZENOH_FASTAPI_KEY", str(key))
    config = Mock()
    monkeypatch.setattr("src.config.zenoh.zenoh.Config", Mock(return_value=config))

    result = get_zenoh_config()

    assert result is config
    assert config.insert_json5.call_count == 6
    config.insert_json5.assert_any_call("mode", '"client"')
    config.insert_json5.assert_any_call(
        "connect/endpoints", "['tls/127.0.0.1:7448']"
    )
    config.insert_json5.assert_any_call("transport/link/tls/enable_mtls", "true")


def test_get_zenoh_config_raises_when_certificate_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.config.zenoh.settings.ZENOH_CA_CERT", str(tmp_path / "missing.crt")
    )

    with pytest.raises(FileNotFoundError):
        get_zenoh_config()
