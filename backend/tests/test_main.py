from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI

import src.main as main


def _clear_zenoh_state(app: FastAPI) -> None:
    for name in (
        "zenoh_session",
        "zenoh_query_handler",
        "zenoh_message_handler",
    ):
        if hasattr(app.state, name):
            delattr(app.state, name)


async def test_lifespan_initializes_and_closes_all_dependencies(monkeypatch):
    app = FastAPI()
    _clear_zenoh_state(app)
    connection = Mock()
    connection.run_sync = AsyncMock()

    class Engine:
        @asynccontextmanager
        async def begin(self):
            yield connection

    valkey = Mock()
    valkey.ping = AsyncMock()
    valkey.close = AsyncMock()
    query_handler = Mock()
    message_handler = Mock()
    session = Mock()
    monkeypatch.setattr(main, "engine", Engine())
    monkeypatch.setattr(main, "init_http_client", Mock())
    monkeypatch.setattr(main, "initialize_backend_auth", Mock())
    monkeypatch.setattr(main, "get_zenoh_config", Mock(return_value="config"))
    monkeypatch.setattr(main.zenoh, "open", Mock(return_value=session))
    monkeypatch.setattr(main, "ZenohQueryHandler", Mock(return_value=query_handler))
    monkeypatch.setattr(main, "ZenohMessageHandler", Mock(return_value=message_handler))
    monkeypatch.setattr(main, "register_handlers", Mock())
    monkeypatch.setattr(main, "close_valkey_pool", AsyncMock())
    monkeypatch.setattr(main, "close_http_client", AsyncMock())

    monkeypatch.setattr("src.config.get_valkey_client", Mock(return_value=valkey))

    async with main.lifespan(app):
        connection.run_sync.assert_awaited_once()
        valkey.ping.assert_awaited_once()
        valkey.close.assert_awaited_once()
        main.register_handlers.assert_called_once_with(query_handler)

    query_handler.close.assert_called_once()
    message_handler.close.assert_called_once()
    session.close.assert_called_once()
    main.close_valkey_pool.assert_awaited_once()
    main.close_http_client.assert_awaited_once()


async def test_lifespan_survives_dependency_startup_failures(monkeypatch):
    app = FastAPI()
    _clear_zenoh_state(app)

    class BrokenEngine:
        @asynccontextmanager
        async def begin(self):
            raise RuntimeError("database unavailable")
            yield  # pragma: no cover

    valkey = Mock()
    valkey.ping = AsyncMock(side_effect=RuntimeError("valkey unavailable"))
    monkeypatch.setattr(main, "engine", BrokenEngine())
    monkeypatch.setattr(main, "init_http_client", Mock())
    monkeypatch.setattr(main, "initialize_backend_auth", Mock())
    monkeypatch.setattr(
        main, "get_zenoh_config", Mock(side_effect=FileNotFoundError("cert"))
    )
    monkeypatch.setattr(main, "close_valkey_pool", AsyncMock())
    monkeypatch.setattr(main, "close_http_client", AsyncMock())
    monkeypatch.setattr("src.config.get_valkey_client", Mock(return_value=valkey))

    async with main.lifespan(app):
        assert not hasattr(app.state, "zenoh_session")

    main.close_valkey_pool.assert_awaited_once()
    main.close_http_client.assert_awaited_once()
