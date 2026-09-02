import pytest

pytestmark = pytest.mark.api


async def test_health_reports_real_postgres_and_valkey(api_client):
    response = await api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "postgres": "healthy",
        "valkey": "healthy",
    }
