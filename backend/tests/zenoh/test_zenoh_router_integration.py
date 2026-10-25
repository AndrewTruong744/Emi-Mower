import subprocess
from pathlib import Path

import httpx
import pytest

from src.config.zenoh_client import ZenohAdminClient

pytestmark = pytest.mark.zenoh_integration


def management_token():
    return subprocess.check_output(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.test.yml",
            "exec",
            "-T",
            "backend",
            "cat",
            "/run/emi-mower/admin/token",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
    ).strip()


async def test_zenoh_router_accepts_dynamic_user_acl_configuration(compose_stack):
    async with httpx.AsyncClient(timeout=10) as client:
        admin = ZenohAdminClient(
            "http://127.0.0.1:18001", http_client=client, admin_token=management_token()
        )
        await admin.configure_user_app("integration-user", ["mower-1"])
        await admin.configure_user_app("integration-user", [])
        await admin.revoke_user("integration-user")
        assert (
            await client.get("http://127.0.0.1:18001/@/runtime/connections")
        ).status_code == 401
