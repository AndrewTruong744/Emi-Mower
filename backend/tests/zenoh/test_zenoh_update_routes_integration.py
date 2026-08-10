"""Transport-level tests for authenticated Zenoh update queryables."""

import asyncio
import json
import time

import pytest

import zenoh

pytestmark = pytest.mark.zenoh_integration


def _query_invalid_token(key_expr: str, payload: dict) -> dict:
    """Query a Compose-hosted backend route and decode its error reply."""
    config = zenoh.Config()
    config.insert_json5("connect/endpoints", '["tcp/127.0.0.1:17447"]')

    session = zenoh.open(config)
    try:
        replies = session.get(
            key_expr,
            payload=json.dumps(payload).encode("utf-8"),
            timeout=5,
        )
        deadline = time.monotonic() + 7
        while True:
            try:
                reply = replies.try_recv()
            except zenoh.ZError as error:
                raise AssertionError(
                    f"No reply received for Zenoh key expression {key_expr!r}"
                ) from error
            if reply is not None:
                break
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"No reply received for Zenoh key expression {key_expr!r}"
                )
            time.sleep(0.05)
        assert reply.err is not None
        return json.loads(reply.err.payload.to_bytes().decode("utf-8"))
    finally:
        session.close()


@pytest.mark.parametrize(
    ("key_expr", "payload"),
    [
        (
            "user/add_mower",
            {"id_token": "not-a-google-token", "mower_id": "mower-1"},
        ),
        (
            "user/update_name",
            {"id_token": "not-a-google-token", "new_user_name": "NewName"},
        ),
        (
            "mower/mower-1/update_name",
            {"id_token": "not-a-google-token", "new_name": "NewMower"},
        ),
        (
            "user/update_email",
            {
                "id_token": "not-a-google-token",
                "new_id_token": "not-a-new-google-token",
            },
        ),
    ],
)
async def test_compose_backend_exposes_update_queryable_and_rejects_invalid_token(
    compose_stack, key_expr, payload
):
    problem = await asyncio.to_thread(_query_invalid_token, key_expr, payload)

    assert problem["status"] == 401
    assert problem["code"] == "authentication-failed"
    assert problem["instance"] == key_expr
