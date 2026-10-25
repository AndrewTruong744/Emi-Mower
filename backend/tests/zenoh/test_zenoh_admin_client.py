import json

import httpx
import pytest

from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import ExternalServiceError

TOKEN = "local-test-management-token-32-bytes"


async def test_principal_rules_enforce_direction_and_owned_mowers():
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        admin = ZenohAdminClient(
            "http://app", "http://mower", client, admin_token=TOKEN
        )
        await admin.configure_user_app("alice", ["A"])
        await admin.configure_user_app("alice", [])
    assert len(requests) == 2
    assert requests[0].url.path == "/@/runtime/principals/alice"
    assert requests[0].headers["Authorization"] == f"Bearer {TOKEN}"
    rules = json.loads(requests[0].content)["rules"]
    joystick = next(r for r in rules if r["id"] == "joystick")
    assert joystick["flows"] == ["ingress"]
    assert joystick["messages"] == ["put"]
    assert joystick["key_exprs"] == ["mower/A/joystick"]
    command_query = next(r for r in rules if r["id"] == "mower-query")
    assert "mower/A/command" in command_query["key_exprs"]
    assert all("mower/B/" not in key for key in command_query["key_exprs"])
    assert all(
        "declare_queryable" not in r["messages"]
        for r in rules
        if "ingress" in r["flows"]
    )
    assert all(
        "mower/" not in k
        for r in json.loads(requests[1].content)["rules"]
        if "ingress" in r["flows"]
        for k in r["key_exprs"]
    )
    assert "password" not in requests[0].content.decode()


async def test_identity_and_connection_management():
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        admin = ZenohAdminClient(
            "http://app", "http://mower", client, admin_token=TOKEN
        )
        await admin.configure_mower_device("A")
        context = {"id": "a" * 32, "nonce": "b" * 32}
        await admin.authorize_connection("alice", context, 300)
        assert await admin.captured_connections() == []
        await admin.revoke_connection(context["id"])
        await admin.revoke_user("alice")
        await admin.remove_mower_permissions("A")
        for invalid in [
            {},
            {"id": 123, "nonce": "b" * 32},
            {"id": "a" * 32, "nonce": "forged"},
        ]:
            with pytest.raises(ValueError):
                await admin.authorize_connection("alice", invalid, 300)
    policy = json.loads(requests[0].content)
    assert policy["subject"]["cert_common_names"] == ["mower:A"]
    assert len({r["id"] for r in policy["rules"]}) == len(policy["rules"])
    assert json.loads(requests[1].content) == {
        "principal": "alice",
        "nonce": "b" * 32,
        "ttl_seconds": 300,
    }
    assert requests[-1].url.path == "/@/runtime/policies/mower-A"
    assert requests[-1].method == "DELETE"


@pytest.mark.parametrize("status", [401, 400, 500])
async def test_management_failures_are_sanitized(status):
    async def respond(request):
        return httpx.Response(status, text="secret router diagnostic")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        admin = ZenohAdminClient("http://app", http_client=client, admin_token=TOKEN)
        with pytest.raises(ExternalServiceError, match="administration failed"):
            await admin.revoke_user("alice")


async def test_transport_failure_is_domain_error():
    async def respond(request):
        raise httpx.ConnectError("offline", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        admin = ZenohAdminClient("http://app", http_client=client, admin_token=TOKEN)
        with pytest.raises(ExternalServiceError):
            await admin.configure_user_app("alice", [])


async def test_retired_identity_cannot_query_publish_or_subscribe():
    captured = []

    async def respond(request):
        captured.append(request)
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        await ZenohAdminClient(
            "http://app", http_client=http, admin_token=TOKEN
        ).retire_user("old")
    rules = json.loads(captured[0].content)["rules"]
    assert rules == [
        {
            "id": "account-switch-reply",
            "permission": "allow",
            "key_exprs": ["user/update_email"],
            "messages": ["reply"],
            "flows": ["egress"],
        }
    ]
