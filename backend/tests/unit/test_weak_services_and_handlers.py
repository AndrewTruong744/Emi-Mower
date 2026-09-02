"""Unit coverage for external-service failure paths and callback bridges."""

from unittest.mock import AsyncMock, Mock

import pytest

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
        self.payload = payload
        self.replies = []
        self.errors = []

    def reply(self, key_expr, payload):
        self.replies.append((str(key_expr), payload))

    def reply_err(self, payload):
        self.errors.append(payload)


class Sample:
    def __init__(self, payload=b"{}"):
        self.payload = payload


async def test_auth_verification_accepts_uid_and_user_id_claims(monkeypatch):
    verify = Mock(return_value={"uid": "uid-1"})
    monkeypatch.setattr(auth_module.auth, "verify_id_token", verify)

    assert await auth_module.verify_zenoh_google_id_token("token") == {"uid": "uid-1"}
    verify.assert_called_once_with("token", clock_skew_seconds=10)

    verify.reset_mock()
    verify.return_value = {"user_id": "legacy-user"}
    assert (await auth_module.verify_zenoh_google_id_token("token"))[
        "user_id"
    ] == "legacy-user"


async def test_auth_verification_rejects_empty_missing_and_invalid_tokens(monkeypatch):
    with pytest.raises(auth_module.ValidationError):
        await auth_module.verify_zenoh_google_id_token("")

    monkeypatch.setattr(auth_module.auth, "verify_id_token", Mock(return_value={}))
    with pytest.raises(AuthenticationError):
        await auth_module.verify_zenoh_google_id_token("token")

    monkeypatch.setattr(
        auth_module.auth, "verify_id_token", Mock(side_effect=ValueError("bad"))
    )
    with pytest.raises(AuthenticationError, match="Invalid, expired"):
        await auth_module.verify_zenoh_google_id_token("token")


def test_initialize_backend_auth_supports_disabled_existing_and_first_start(
    monkeypatch,
):
    monkeypatch.setenv("FIREBASE_DISABLED", "true")
    assert firebase_module.initialize_backend_auth() is None

    monkeypatch.delenv("FIREBASE_DISABLED")
    existing = object()
    monkeypatch.setattr(
        firebase_module.firebase_admin, "get_app", Mock(return_value=existing)
    )
    assert firebase_module.initialize_backend_auth() is existing

    monkeypatch.setattr(
        firebase_module.firebase_admin, "get_app", Mock(side_effect=ValueError())
    )
    certificate = Mock(return_value="certificate")
    initialize = Mock(return_value="initialized")
    monkeypatch.setattr(firebase_module.credentials, "Certificate", certificate)
    monkeypatch.setattr(firebase_module.firebase_admin, "initialize_app", initialize)
    assert firebase_module.initialize_backend_auth() == "initialized"
    certificate.assert_called_once()
    initialize.assert_called_once_with(credential="certificate")


def test_jwt_generation_handles_string_bytes_and_failures(monkeypatch):
    monkeypatch.setattr(jwt_module.jwt, "encode", Mock(return_value=b"encoded"))
    assert jwt_module.generate_jwt_token("user-1") == "encoded"

    monkeypatch.setattr(
        jwt_module.jwt, "encode", Mock(side_effect=RuntimeError("jwt down"))
    )
    with pytest.raises(TokenGenerationError):
        jwt_module.generate_jwt_token("user-1")


def test_payload_bytes_and_problem_mapping_cover_fallbacks():
    class Payload:
        def to_bytes(self):
            return b"payload"

    assert handler_module._payload_bytes(None) == b""
    assert handler_module._payload_bytes(Payload()) == b"payload"
    assert handler_module._payload_bytes(bytearray(b"bytes")) == b"bytes"

    unknown_domain = _exception_problem(RepositoryError("repository"), "one")
    assert unknown_domain.status == 500
    generic = _exception_problem(RuntimeError("unexpected"), "one")
    assert generic.code == "internal-error"


def test_query_declaration_schedules_and_waits_for_callback(monkeypatch):
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
    future.result.assert_called_once_with(timeout=5)
    assert handler.queryables == [queryable]


def test_query_declaration_logs_callback_timeout(monkeypatch):
    future = Mock()
    future.result.side_effect = TimeoutError("slow")
    session = Mock()

    def schedule(coroutine, _loop):
        coroutine.close()
        return future

    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohQueryHandler(session, Mock())
    handler.declare("user/login", AsyncMock())
    session.declare_queryable.call_args.args[1](Query())
    future.result.assert_called_once()


def test_message_declaration_schedules_and_logs_completion(monkeypatch):
    futures = []

    class Future:
        def __init__(self, error=None):
            self.error = error

        def add_done_callback(self, callback):
            callback(self)

        def result(self):
            if self.error:
                raise self.error

    session = Mock()
    session.declare_subscriber.return_value = object()

    def schedule(coroutine, _loop):
        coroutine.close()
        futures.append(Future())
        return futures[-1]

    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohMessageHandler(session, Mock())
    handler.declare("mower/*", AsyncMock())
    session.declare_subscriber.call_args.args[1](Sample())
    assert len(futures) == 1

    handler_module.ZenohMessageHandler._log_failure(Future(), "mower/*")
    handler_module.ZenohMessageHandler._log_failure(
        Future(RuntimeError("failed")), "mower/*"
    )


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


def test_message_declaration_returns_cleanly_when_scheduling_fails(monkeypatch):
    session = Mock()
    session.declare_subscriber.return_value = object()

    def schedule(coroutine, _loop):
        coroutine.close()
        raise RuntimeError("loop stopped")

    monkeypatch.setattr(handler_module.asyncio, "run_coroutine_threadsafe", schedule)
    handler = ZenohMessageHandler(session, Mock())
    handler.declare("mower/*", AsyncMock())
    session.declare_subscriber.call_args.args[1](Sample())
