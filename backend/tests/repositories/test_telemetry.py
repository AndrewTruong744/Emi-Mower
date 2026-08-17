from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.exceptions import RepositoryError
from src.repositories import telemetry
from src.schemas.valkey import mower_telemetry_key
from src.zenoh.generated import TelemetryRecord


def record(mower_id: str, *, with_imu: bool = False) -> TelemetryRecord:
    return TelemetryRecord(
        mower_id=mower_id,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        latitude=1.0,
        longitude=2.0,
        battery_percentage=90,
        imu_data=(
            {
                "accel_x": 1,
                "accel_y": 2,
                "accel_z": 3,
                "gyro_x": 4,
                "gyro_y": 5,
                "gyro_z": 6,
                "mag_x": 7,
                "mag_y": 8,
                "mag_z": 9,
            }
            if with_imu
            else None
        ),
    )


@asynccontextmanager
async def client_context(client):
    yield client


@pytest.mark.asyncio
async def test_add_telemetry_to_cache_groups_records_by_mower(monkeypatch):
    client = Mock()
    client.rpush = AsyncMock()
    monkeypatch.setattr(telemetry, "get_valkey_client", lambda: client_context(client))
    records = [record("mower-1"), record("mower-1"), record("mower-2")]

    assert await telemetry.add_telemetry_to_cache(records) == 3

    assert client.rpush.await_count == 2
    client.rpush.assert_any_await(
        mower_telemetry_key("mower-1"),
        records[0].model_dump_json(),
        records[1].model_dump_json(),
    )
    client.rpush.assert_any_await(
        mower_telemetry_key("mower-2"), records[2].model_dump_json()
    )


@pytest.mark.asyncio
async def test_add_telemetry_to_cache_wraps_valkey_failures(monkeypatch):
    client = Mock()
    client.rpush = AsyncMock(side_effect=RuntimeError("cache down"))
    monkeypatch.setattr(telemetry, "get_valkey_client", lambda: client_context(client))

    with pytest.raises(RepositoryError):
        await telemetry.add_telemetry_to_cache([record("mower-1")])


@pytest.mark.asyncio
async def test_push_cached_telemetry_builds_database_models_with_imu():
    db = Mock()
    db.add_all = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    mower_id = str(uuid4())

    inserted = await telemetry.push_cached_telemetry_to_db(
        [record(mower_id, with_imu=True), record("invalid-mower")], db
    )

    assert inserted == 1
    db.add_all.assert_called_once()
    models = db.add_all.call_args.args[0]
    assert models[0].mower_id.hex == mower_id.replace("-", "")
    assert models[0].imu_data.accel_x == 1
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_push_cached_telemetry_returns_zero_for_no_valid_records():
    db = Mock()
    db.add_all = Mock()
    db.commit = AsyncMock()

    assert await telemetry.push_cached_telemetry_to_db(
        [record("invalid-mower")], db
    ) == 0

    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_push_cached_telemetry_rolls_back_database_failure():
    db = Mock()
    db.add_all = Mock()
    db.commit = AsyncMock(side_effect=RuntimeError("database down"))
    db.rollback = AsyncMock()

    with pytest.raises(RepositoryError):
        await telemetry.push_cached_telemetry_to_db([record(str(uuid4()))], db)

    db.rollback.assert_awaited_once()
