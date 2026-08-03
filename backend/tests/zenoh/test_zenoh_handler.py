from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

from src.exceptions import OwnershipError
from src.zenoh.generated import UserLoginRequest
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


async def test_query_handler_returns_problem_details_for_invalid_payload(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    query = FakeQuery(b"not-json")
    handler = ZenohQueryHandler(Mock(), Mock())

    await handler._process(query, AsyncMock(), UserLoginRequest)

    assert query.replies == []
    assert b'"status":400' in query.errors[0]


async def test_message_handler_validates_and_delegates(monkeypatch):
    import src.zenoh.zenoh_handler as handlers

    monkeypatch.setattr(handlers, "AsyncSessionLocal", fake_db_session)
    callback = AsyncMock()
    handler = ZenohMessageHandler(Mock(), Mock())

    await handler._process(
        FakeSample(b'{"id_token":"token"}'), callback, UserLoginRequest
    )

    callback.assert_awaited_once()
