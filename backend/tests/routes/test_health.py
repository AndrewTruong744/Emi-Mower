from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.health import _dependency_status, health_check


async def test_dependency_status_reports_both_dependencies_healthy():
    db = AsyncMock()
    cache = AsyncMock()

    assert await _dependency_status(db, cache) == {
        "postgres": "healthy",
        "valkey": "healthy",
    }


async def test_dependency_status_reports_each_dependency_failure_independently():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("postgres unavailable")
    cache = AsyncMock()
    cache.ping.side_effect = RuntimeError("valkey unavailable")

    assert await _dependency_status(db, cache) == {
        "postgres": "unhealthy",
        "valkey": "unhealthy",
    }


async def test_health_check_returns_status_when_dependencies_are_healthy():
    db = AsyncMock()
    cache = AsyncMock()

    assert await health_check(db, cache) == {
        "status": "healthy",
        "postgres": "healthy",
        "valkey": "healthy",
    }


async def test_health_check_raises_503_when_dependency_is_unhealthy():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("postgres unavailable")
    cache = AsyncMock()

    with pytest.raises(HTTPException) as error:
        await health_check(db, cache)

    assert error.value.status_code == 503
    assert error.value.detail["status"] == "unhealthy"
