"""Transport-level tests for authenticated Zenoh update queryables."""

import asyncio
import json

import pytest

import zenoh
from src.config.zenoh_client import ZenohAdminClient

pytestmark = pytest.mark.zenoh_integration


def _query_invalid_token(key_expr: str, payload: dict) -> dict:
    """Query a Compose-hosted backend route and decode its error reply."""
    config = zenoh.Config()
    config.insert_json5("connect/endpoints", '["tcp/127.0.0.1:17447"]')
    config.insert_json5("transport/auth/usrpwd/user", '"integration-user"')
    config.insert_json5("transport/auth/usrpwd/password", '"jwt"')

    session = zenoh.open(config)
    try:
        replies = session.get(
            key_expr,
            payload=json.dumps(payload).encode("utf-8"),
            timeout=10,
        )
        reply = next(iter(replies))
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
    admin = ZenohAdminClient("http://127.0.0.1:18001")
    await admin.configure_user_app("integration-user", ["mower-1"], password="jwt")

    problem = await asyncio.to_thread(_query_invalid_token, key_expr, payload)

    assert problem["status"] == 401
    assert problem["code"] == "authentication-failed"
    assert problem["instance"] == key_expr
