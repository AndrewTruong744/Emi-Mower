from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import OwnershipError
from src.zenoh.generated import TelemetryList, UserLoginRequest
from src.zenoh.zenoh_handler import (
    ZenohMessageHandler,
    ZenohQueryHandler,
    _exception_problem,
)


class FakeQuery:
    key_expr = "user/login"

    def __init__(self, payload: bytes):
        self.payload = payload
        self.replies = []
        self.errors = []

    def reply(self, key_expr, payload):
        self.replies.append((str(key_expr), payload))

    def reply_err(self, payload):
        self.errors.append(payload)


class FakeSample:
    def __init__(self, payload: bytes):
        self.payload = payload


@asynccontextmanager
async def fake_db_session():
    yield object()


def test_exception_problem_maps_domain_exception_to_wire_contract():
    problem = _exception_problem(OwnershipError("not owner"), "mower/one")

    assert problem.status == 403
    assert problem.code == "ownership-failed"
    assert problem.instance == "mower/one"


async def test_query_handler_validates_request_and_replies_json(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    callback = AsyncMock(return_value={"ok": True})
    query = FakeQuery(b'{"id_token":"token"}')
    handler = ZenohQueryHandler(Mock(), Mock())

    await handler._process(query, callback, UserLoginRequest)

    callback.assert_awaited_once()
    assert query.replies == [("user/login", b'{"ok": true}')]
    assert query.errors == []


async def test_query_handler_can_pass_concrete_query_key_to_listener(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    callback = AsyncMock(return_value={"ok": True})
    query = FakeQuery(b"{}")
    query.key_expr = "mower/mower-1/livekit/consume"
    handler = ZenohQueryHandler(Mock(), Mock())

    await handler._process(query, callback, None, include_query_key=True)

    callback.assert_awaited_once()
    assert callback.await_args.args[0] == {}
    assert callback.await_args.args[2] == query.key_expr


async def test_query_handler_returns_problem_details_for_invalid_payload(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    query = FakeQuery(b"not-json")
    handler = ZenohQueryHandler(Mock(), Mock())

    await handler._process(query, AsyncMock(), UserLoginRequest)

    assert query.replies == []
    assert b'"status":400' in query.errors[0]


async def test_query_handler_rejects_non_object_json_payload(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    query = FakeQuery(b'["not", "an", "object"]')
    handler = ZenohQueryHandler(Mock(), Mock())

    await handler._process(query, AsyncMock(), UserLoginRequest)

    assert b'"status":400' in query.errors[0]


async def test_message_handler_rejects_non_object_payload(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    handler = ZenohMessageHandler(Mock(), Mock())

    with pytest.raises(ValueError):
        await handler._process(
            FakeSample(b'["not", "an", "object"]'), AsyncMock(), UserLoginRequest
        )


def test_handlers_close_undeclares_registered_handles():
    queryable = Mock()
    subscriber = Mock()
    query_handler = ZenohQueryHandler(Mock(), Mock())
    message_handler = ZenohMessageHandler(Mock(), Mock())
    query_handler.queryables.append(queryable)
    message_handler.subscribers.append(subscriber)

    query_handler.close()
    message_handler.close()

    queryable.undeclare.assert_called_once()
    subscriber.undeclare.assert_called_once()


async def test_message_handler_validates_and_delegates(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    callback = AsyncMock()
    handler = ZenohMessageHandler(Mock(), Mock())

    await handler._process(
        FakeSample(b'{"id_token":"token"}'), callback, UserLoginRequest
    )

    callback.assert_awaited_once()


async def test_message_handler_accepts_root_model_lists(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    callback = AsyncMock()
    handler = ZenohMessageHandler(Mock(), Mock())
    payload = TelemetryList(
        [
            {
                "mower_id": "mower-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "latitude": 1,
                "longitude": 2,
                "battery_percentage": 90,
            }
        ]
    )

    await handler._process(
        FakeSample(payload.model_dump_json().encode()),
        callback,
        TelemetryList,
    )

    callback.assert_awaited_once()
    assert callback.await_args.args[0].root[0].mower_id == "mower-1"
