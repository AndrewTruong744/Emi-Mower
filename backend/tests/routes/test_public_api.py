import pytest

pytestmark = pytest.mark.api


async def test_liveness_is_available_through_full_compose_stack(api_client):
    response = await api_client.get("/api/v1/public/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_readiness_reports_real_postgres_and_valkey(api_client):
    response = await api_client.get("/api/v1/public/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "postgres": "healthy",
        "valkey": "healthy",
    }
