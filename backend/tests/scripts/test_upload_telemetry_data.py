from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.scripts import upload_telemetry_data as worker
from src.zenoh.generated import TelemetryRecord


def telemetry_json(mower_id: str) -> str:
    return TelemetryRecord(
        mower_id=mower_id,
        timestamp=datetime.now(timezone.utc),
        latitude=1.0,
        longitude=2.0,
        battery_percentage=90,
    ).model_dump_json()


@asynccontextmanager
async def session_context(session):
    yield session


@pytest.mark.asyncio
async def test_process_key_deletes_empty_temp_list():
    client = Mock()
    client.lrange = AsyncMock(return_value=[])
    client.delete = AsyncMock()

    await worker.process_key(client, "mower:one:telemetry:data:temp")

    client.delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_process_key_skips_invalid_records_and_cleans_key(monkeypatch):
    client = Mock()
    client.lrange = AsyncMock(return_value=["not-json", telemetry_json("not-a-uuid")])
    client.delete = AsyncMock()
    session = Mock()
    push = AsyncMock(return_value=0)
    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: session_context(session))
    monkeypatch.setattr(worker, "push_cached_telemetry_to_db", push)

    await worker.process_key(client, "mower:one:telemetry:data:temp")

    push.assert_awaited_once()
    client.delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_process_key_persists_valid_record_with_nested_imu(monkeypatch):
    mower_id = str(uuid4())
    record = TelemetryRecord(
        mower_id=mower_id,
        timestamp=datetime.now(timezone.utc),
        latitude=1.0,
        longitude=2.0,
        battery_percentage=90,
        imu_data={
            "accel_x": 1,
            "accel_y": 2,
            "accel_z": 3,
            "gyro_x": 4,
            "gyro_y": 5,
            "gyro_z": 6,
            "mag_x": 7,
            "mag_y": 8,
            "mag_z": 9,
        },
    )
    client = Mock()
    client.lrange = AsyncMock(return_value=[record.model_dump_json()])
    client.delete = AsyncMock()
    session = Mock()
    push = AsyncMock(return_value=1)
    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: session_context(session))
    monkeypatch.setattr(worker, "push_cached_telemetry_to_db", push)

    await worker.process_key(client, "mower:one:telemetry:data:temp")

    push.assert_awaited_once()
    persisted_records = push.await_args.args[0]
    assert len(persisted_records) == 1
    assert persisted_records[0].imu_data is not None
    client.delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_process_key_keeps_temp_key_when_repository_fails(monkeypatch):
    client = Mock()
    client.lrange = AsyncMock(return_value=[telemetry_json(str(uuid4()))])
    client.delete = AsyncMock()
    session = Mock()
    monkeypatch.setattr(worker, "AsyncSessionLocal", lambda: session_context(session))
    monkeypatch.setattr(
        worker,
        "push_cached_telemetry_to_db",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    await worker.process_key(client, "mower:one:telemetry:data:temp")

    client.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_sync_cycle_renames_active_keys_before_processing(monkeypatch):
    client = Mock()
    client.keys = AsyncMock(side_effect=[[], ["mower:mower-1:telemetry:data"]])
    client.rename = AsyncMock()
    process = AsyncMock()
    monkeypatch.setattr(worker, "get_valkey_client", Mock(return_value=client))
    monkeypatch.setattr(worker, "process_key", process)

    await worker.run_sync_cycle()

    client.rename.assert_awaited_once_with(
        "mower:mower-1:telemetry:data", "mower:mower-1:telemetry:data:temp"
    )
    process.assert_awaited_once_with(client, "mower:mower-1:telemetry:data:temp")


@pytest.mark.asyncio
async def test_run_sync_cycle_is_noop_when_valkey_has_no_telemetry_keys(monkeypatch):
    client = Mock()
    client.keys = AsyncMock(side_effect=[[], []])
    client.rename = AsyncMock()
    process = AsyncMock()
    monkeypatch.setattr(worker, "get_valkey_client", Mock(return_value=client))
    monkeypatch.setattr(worker, "process_key", process)

    await worker.run_sync_cycle()

    client.keys.assert_any_await(worker.MOWER_TELEMETRY_TEMP_PATTERN)
    client.keys.assert_any_await(worker.MOWER_TELEMETRY_PATTERN)
    client.rename.assert_not_awaited()
    process.assert_not_awaited()
