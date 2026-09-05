"""Shared test infrastructure.

Unit tests run without Docker. ``--run-integration`` starts disposable
Testcontainers for repository cache-aside tests; tests marked ``api`` or
``zenoh_integration`` additionally start ``docker-compose.test.yml`` once.
"""

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parents[1]
INTEGRATION_MARKERS = {"repository", "api", "zenoh_integration"}
TABLES = "cutout_mower_assignments, cutouts, mower_imu_data, mower_telemetry, yard_coordinates, yards, mowers, users"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run Docker-backed repository, Zenoh, and API integration tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    if not config.getoption("--run-integration"):
        return

    # This hook runs before test collection, which is essential: database.py
    # and valkey_client.py construct their clients at import time.
    from testcontainers.core.container import DockerContainer
    from testcontainers.postgres import PostgresContainer

    postgres = PostgresContainer(
        "postgres:18-alpine",
        username="test",
        password="test",
        dbname="emi_mower_test",
    )
    valkey = DockerContainer("valkey/valkey:9-alpine").with_exposed_ports(6379)
    try:
        postgres.start()
        valkey.start()
        os.environ.update(
            {
                "POSTGRES_HOST": postgres.get_container_host_ip(),
                "POSTGRES_PORT": str(postgres.get_exposed_port(5432)),
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_DB": "emi_mower_test",
                "VALKEY_HOST": valkey.get_container_host_ip(),
                "VALKEY_PORT": str(valkey.get_exposed_port(6379)),
                "VALKEY_DB": "0",
            }
        )
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            check=True,
        )
    except Exception:
        valkey.stop()
        postgres.stop()
        raise
    config._emi_testcontainers = (postgres, valkey)  # type: ignore[attr-defined]


def pytest_unconfigure(config: pytest.Config) -> None:
    containers = getattr(config, "_emi_testcontainers", None)
    if containers is not None:
        for container in reversed(containers):
            container.stop()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="pass --run-integration to run Docker-backed tests")
    for item in items:
        if any(item.get_closest_marker(marker) for marker in INTEGRATION_MARKERS):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def compose_stack(pytestconfig: pytest.Config) -> AsyncIterator[None]:
    """Start the complete disposable stack only for API/Zenoh tests."""
    if not pytestconfig.getoption("--run-integration"):
        pytest.skip("pass --run-integration to run Docker-backed tests")

    command = ["docker", "compose", "-f", "docker-compose.test.yml"]
    try:
        subprocess.run(
            [*command, "up", "--build", "--wait"],
            cwd=BACKEND_DIR,
            check=True,
            timeout=300,
        )
        yield
    finally:
        subprocess.run(
            [*command, "down", "--timeout", "1", "--volumes", "--remove-orphans"],
            cwd=BACKEND_DIR,
            check=False,
            timeout=120,
        )


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[Any]:
    from src.config.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def cache() -> AsyncIterator[Any]:
    from src.config.valkey_client import get_valkey_client

    async with get_valkey_client() as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def reset_repository_state(
    request: pytest.FixtureRequest, db_session: Any, cache: Any
) -> AsyncIterator[None]:
    if not any(
        request.node.get_closest_marker(marker) for marker in INTEGRATION_MARKERS
    ):
        yield
        return

    await cache.flushdb()
    await db_session.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    await db_session.commit()
    yield
    await cache.flushdb()
    await db_session.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    await db_session.commit()


@pytest_asyncio.fixture
async def seed_user(db_session: Any) -> Callable[..., Any]:
    from src.models.user import UserModel

    async def create(
        user_id: str = "user-1",
        email: str = "user-1@example.test",
        name: str = "UserOne",
    ) -> UserModel:
        user = UserModel(id=user_id, email=email, name=name)
        db_session.add(user)
        await db_session.commit()
        return user

    return create


@pytest_asyncio.fixture
async def seed_mower(db_session: Any) -> Callable[..., Any]:
    from src.models.mower import MowerModel

    async def create(
        *,
        owner_id: str | None = "user-1",
        serial_number: str = "serial-1",
        nickname: str = "MowerOne",
    ) -> MowerModel:
        mower = MowerModel(
            owner_id=owner_id, serial_number=serial_number, nickname=nickname
        )
        db_session.add(mower)
        await db_session.commit()
        await db_session.refresh(mower)
        return mower

    return create


@pytest_asyncio.fixture
async def api_client(compose_stack: None) -> AsyncIterator[Any]:
    import httpx

    async with httpx.AsyncClient(base_url="http://127.0.0.1:18000") as client:
        yield client
