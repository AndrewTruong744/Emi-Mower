import httpx
import pytest

from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import ExternalServiceError


async def test_configure_user_app_writes_password_and_acl_triad():
    requests = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        zenoh = ZenohAdminClient("http://app", "http://mower", client)
        await zenoh.configure_user_app("user-1", ["mower-1"], password="jwt")

    assert len(requests) == 4
    assert requests[0].url.path.endswith("/dictionary/user-1")
    assert b"mower/mower-1/**" in requests[1].content


async def test_zenoh_admin_client_maps_http_failure_to_domain_error():
    async def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="broken", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as client:
        zenoh = ZenohAdminClient("http://app", http_client=client)
        with pytest.raises(ExternalServiceError):
            await zenoh.delete_user_password("user-1")
