from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services import telemetry_buffer
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
async def test_persist_telemetry_buffer_deletes_empty_temp_list(monkeypatch):
    read = AsyncMock(return_value=[])
    delete = AsyncMock()
    monkeypatch.setattr(telemetry_buffer, "read_telemetry_buffer", read)
    monkeypatch.setattr(telemetry_buffer, "delete_telemetry_buffer", delete)

    await telemetry_buffer.persist_telemetry_buffer("mower:one:telemetry:data:temp")

    delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_persist_telemetry_buffer_skips_invalid_records_and_cleans_key(
    monkeypatch,
):
    read = AsyncMock(return_value=["not-json", telemetry_json("not-a-uuid")])
    delete = AsyncMock()
    session = Mock()
    persist = AsyncMock(return_value=0)
    monkeypatch.setattr(
        telemetry_buffer, "AsyncSessionLocal", lambda: session_context(session)
    )
    monkeypatch.setattr(telemetry_buffer, "read_telemetry_buffer", read)
    monkeypatch.setattr(telemetry_buffer, "delete_telemetry_buffer", delete)
    monkeypatch.setattr(telemetry_buffer, "persist_telemetry_records", persist)

    await telemetry_buffer.persist_telemetry_buffer("mower:one:telemetry:data:temp")

    persist.assert_awaited_once()
    delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_persist_telemetry_buffer_persists_valid_record_with_nested_imu(
    monkeypatch,
):
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
    read = AsyncMock(return_value=[record.model_dump_json()])
    delete = AsyncMock()
    session = Mock()
    persist = AsyncMock(return_value=1)
    monkeypatch.setattr(
        telemetry_buffer, "AsyncSessionLocal", lambda: session_context(session)
    )
    monkeypatch.setattr(telemetry_buffer, "read_telemetry_buffer", read)
    monkeypatch.setattr(telemetry_buffer, "delete_telemetry_buffer", delete)
    monkeypatch.setattr(telemetry_buffer, "persist_telemetry_records", persist)

    await telemetry_buffer.persist_telemetry_buffer("mower:one:telemetry:data:temp")

    persist.assert_awaited_once()
    persisted_records = persist.await_args.args[0]
    assert len(persisted_records) == 1
    assert persisted_records[0].imu_data is not None
    delete.assert_awaited_once_with("mower:one:telemetry:data:temp")


@pytest.mark.asyncio
async def test_persist_telemetry_buffer_keeps_temp_key_when_repository_fails(
    monkeypatch,
):
    read = AsyncMock(return_value=[telemetry_json(str(uuid4()))])
    delete = AsyncMock()
    session = Mock()
    monkeypatch.setattr(
        telemetry_buffer, "AsyncSessionLocal", lambda: session_context(session)
    )
    monkeypatch.setattr(telemetry_buffer, "read_telemetry_buffer", read)
    monkeypatch.setattr(telemetry_buffer, "delete_telemetry_buffer", delete)
    monkeypatch.setattr(
        telemetry_buffer,
        "persist_telemetry_records",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    await telemetry_buffer.persist_telemetry_buffer("mower:one:telemetry:data:temp")

    delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_flush_pending_telemetry_buffers_renames_active_keys_before_processing(
    monkeypatch,
):
    persist = AsyncMock()
    claim = AsyncMock(return_value="mower:mower-1:telemetry:data:temp")
    monkeypatch.setattr(
        telemetry_buffer, "list_temporary_telemetry_buffers", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        telemetry_buffer,
        "list_active_telemetry_buffers",
        AsyncMock(return_value=["mower:mower-1:telemetry:data"]),
    )
    monkeypatch.setattr(telemetry_buffer, "claim_active_telemetry_buffer", claim)
    monkeypatch.setattr(telemetry_buffer, "persist_telemetry_buffer", persist)

    await telemetry_buffer.flush_pending_telemetry_buffers()

    claim.assert_awaited_once_with("mower:mower-1:telemetry:data")
    persist.assert_awaited_once_with("mower:mower-1:telemetry:data:temp")


@pytest.mark.asyncio
async def test_flush_pending_telemetry_buffers_is_noop_without_telemetry_keys(
    monkeypatch,
):
    persist = AsyncMock()
    temporary = AsyncMock(return_value=[])
    active = AsyncMock(return_value=[])
    claim = AsyncMock()
    monkeypatch.setattr(telemetry_buffer, "list_temporary_telemetry_buffers", temporary)
    monkeypatch.setattr(telemetry_buffer, "list_active_telemetry_buffers", active)
    monkeypatch.setattr(telemetry_buffer, "claim_active_telemetry_buffer", claim)
    monkeypatch.setattr(telemetry_buffer, "persist_telemetry_buffer", persist)

    await telemetry_buffer.flush_pending_telemetry_buffers()

    temporary.assert_awaited_once()
    active.assert_awaited_once()
    claim.assert_not_awaited()
    persist.assert_not_awaited()
