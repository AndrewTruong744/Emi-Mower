"""Unit coverage for external-service failure paths and callback bridges."""

from unittest.mock import AsyncMock, Mock

import pytest

import zenoh
from src.exceptions import AuthenticationError, RepositoryError, TokenGenerationError
from src.services import auth as auth_module
from src.services import firebase_init as firebase_module
from src.services import temp_jwt as jwt_module
from src.zenoh import zenoh_handler as handler_module
from src.zenoh.zenoh_handler import (
    ZenohMessageHandler,
    ZenohQueryHandler,
    _exception_problem,
)


class Query:
    key_expr = "user/login"

    def __init__(self, payload=b"{}"):
        self.payload = zenoh.ZBytes(payload)
        self.replies = []
        self.errors = []
        self.drops = 0

    def reply(self, key_expr, payload):
        self.replies.append((str(key_expr), payload))

    def reply_err(self, payload):
        self.errors.append(payload)

    def drop(self):
        self.drops += 1


class Sample:
    def __init__(self, payload=b"{}"):
        self.payload = zenoh.ZBytes(payload)


async def test_auth_verification_normalizes_uid_to_user_id(monkeypatch):
    verify = Mock(return_value={"uid": "uid-1"})
    monkeypatch.setattr(auth_module.auth, "verify_id_token", verify)

    assert await auth_module.verify_firebase_id_token("token") == {
        "uid": "uid-1",
        "user_id": "uid-1",
    }
    verify.assert_called_once_with("token", clock_skew_seconds=10)

    verify.reset_mock()
    verify.return_value = {"user_id": "legacy-user"}
    assert (await auth_module.verify_firebase_id_token("token"))[
        "user_id"
    ] == "legacy-user"


async def test_auth_verification_rejects_empty_missing_and_invalid_tokens(monkeypatch):
    with pytest.raises(auth_module.ValidationError):
        await auth_module.verify_firebase_id_token("")

    monkeypatch.setattr(auth_module.auth, "verify_id_token", Mock(return_value={}))
    with pytest.raises(AuthenticationError):
        await auth_module.verify_firebase_id_token("token")

    monkeypatch.setattr(
        auth_module.auth, "verify_id_token", Mock(side_effect=ValueError("bad"))
    )
    with pytest.raises(AuthenticationError, match="Invalid, expired"):
        await auth_module.verify_firebase_id_token("token")


def test_initialize_backend_auth_supports_disabled_existing_and_first_start(
    monkeypatch,
):
    monkeypatch.setattr(firebase_module.settings, "FIREBASE_DISABLED", True)
    assert firebase_module.initialize_backend_auth() is None

    monkeypatch.setattr(firebase_module.settings, "FIREBASE_DISABLED", False)
    existing = object()
    monkeypatch.setattr(
        firebase_module.firebase_admin, "get_app", Mock(return_value=existing)
    )
    assert firebase_module.initialize_backend_auth() is existing

    monkeypatch.setattr(
        firebase_module.firebase_admin, "get_app", Mock(side_effect=ValueError())
    )
    application_default = Mock(return_value="adc")
    initialize = Mock(return_value="initialized")
    monkeypatch.setattr(
        firebase_module.credentials, "ApplicationDefault", application_default
    )
    monkeypatch.setattr(firebase_module.firebase_admin, "initialize_app", initialize)
    assert firebase_module.initialize_backend_auth() == "initialized"
    application_default.assert_called_once()
    initialize.assert_called_once_with(credential="adc")


def test_jwt_generation_handles_string_bytes_and_failures(monkeypatch):
    monkeypatch.setattr(jwt_module.jwt, "encode", Mock(return_value=b"encoded"))
    assert jwt_module.generate_jwt_token("user-1") == "encoded"

    monkeypatch.setattr(
        jwt_module.jwt, "encode", Mock(side_effect=RuntimeError("jwt down"))
    )
    with pytest.raises(TokenGenerationError):
        jwt_module.generate_jwt_token("user-1")


def test_payload_bytes_and_problem_mapping_cover_fallbacks():
    assert handler_module._payload_bytes(None) == b""
    assert handler_module._payload_bytes(zenoh.ZBytes(b"payload")) == b"payload"

    unknown_domain = _exception_problem(RepositoryError("repository"), "one")
    assert unknown_domain.status == 500
    generic = _exception_problem(RuntimeError("unexpected"), "one")
    assert generic.code == "internal-error"


def test_query_declaration_schedules_without_waiting_for_callback(monkeypatch):
    future = Mock()
    session = Mock()
    queryable = object()
    session.declare_queryable.return_value = queryable

    def schedule(coroutine, _loop):
        coroutine.close()
        return future

    schedule = Mock(side_effect=schedule)
    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    loop = Mock()
    handler = ZenohQueryHandler(session, loop)

    assert handler.declare("user/login", AsyncMock()) is queryable
    callback = session.declare_queryable.call_args.args[1]
    callback(Query())

    schedule.assert_called_once()
    future.result.assert_not_called()
    future.add_done_callback.assert_not_called()
    assert handler.queryables == [queryable]


def test_query_declaration_logs_scheduling_failure(monkeypatch, caplog):
    session = Mock()

    def schedule(coroutine, _loop):
        raise RuntimeError("loop stopped")

    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohQueryHandler(session, Mock())
    handler.declare("user/login", AsyncMock())
    session.declare_queryable.call_args.args[1](Query())
    assert "Failed to schedule Zenoh query for user/login" in caplog.text


def test_message_declaration_schedules_without_waiting(monkeypatch):
    future = Mock()
    session = Mock()
    session.declare_subscriber.return_value = object()

    def schedule(coroutine, _loop):
        coroutine.close()
        return future

    schedule = Mock(side_effect=schedule)
    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohMessageHandler(session, Mock())
    handler.declare("mower/*", AsyncMock())
    session.declare_subscriber.call_args.args[1](Sample())
    schedule.assert_called_once()
    future.result.assert_not_called()
    future.add_done_callback.assert_not_called()


async def test_query_handler_maps_unhandled_handler_failure(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    class DbContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(handlers, "AsyncSessionLocal", lambda: DbContext())
    query = Query()

    async def fail(*_args):
        raise RuntimeError("unexpected")

    await ZenohQueryHandler(Mock(), Mock())._process(query, fail, None)

    assert b'"code":"internal-error"' in query.errors[0]
    assert query.drops == 1


def test_message_declaration_returns_cleanly_when_scheduling_fails(monkeypatch):
    session = Mock()
    session.declare_subscriber.return_value = object()
    scheduled = []

    def schedule(coroutine, _loop):
        scheduled.append(coroutine)
        raise RuntimeError("loop stopped")

    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohMessageHandler(session, Mock())
    handler.declare("mower/*", AsyncMock())
    session.declare_subscriber.call_args.args[1](Sample())
    assert scheduled[0].cr_frame is None
