import httpx
import pytest

from src.config.zenoh_client import ZenohAdminClient

pytestmark = pytest.mark.zenoh_integration


async def test_zenoh_router_accepts_dynamic_user_acl_configuration(compose_stack):
    async with httpx.AsyncClient(timeout=10) as client:
        zenoh = ZenohAdminClient("http://127.0.0.1:18001", http_client=client)
        await zenoh.configure_user_app("integration-user", ["mower-1"], password="jwt")
