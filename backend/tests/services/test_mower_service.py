from unittest.mock import ANY, AsyncMock

import pytest

from src.exceptions import MowerNotFoundError, OwnershipError, ValidationError
from src.services import mower
from src.zenoh.generated import TelemetryHistoryPoint, TelemetryRecord


async def test_get_mower_data_service_returns_only_requested_mower(monkeypatch):
    expected = {"id": "mower-1", "nickname": "One"}
    monkeypatch.setattr(mower, "get_mower_data", AsyncMock(return_value=[expected]))

    assert await mower.get_mower_data_service("user-1", "mower-1", object()) == expected


async def test_add_telemetry_data_service_delegates_to_repository(monkeypatch):
    add = AsyncMock()
    monkeypatch.setattr(mower, "add_telemetry_to_cache", add)
    telemetry_data = [
        TelemetryRecord(
            mower_id="mower-1",
            timestamp="2026-01-01T00:00:00Z",
            latitude=1,
            longitude=2,
            battery_percentage=90,
        )
    ]

    await mower.add_telemetry_data_service(telemetry_data)

    add.assert_awaited_once_with(telemetry_data)


async def test_telemetry_history_service_requires_ownership_and_returns_cursor_page(
    monkeypatch,
):
    monkeypatch.setattr(mower, "verify_ownership", AsyncMock(return_value=True))
    history = AsyncMock(
        return_value=(
            61,
            [("2026-01-01T00:00:00Z", 0.5, "record-id")],
            "cursor-2",
        )
    )
    monkeypatch.setattr(mower, "get_telemetry_history", history)

    result = await mower.get_telemetry_history_service(
        "user-1", "mower-1", "accel_x", "cursor-1", object()
    )

    assert result.has_more is True
    assert result.next_cursor == "cursor-2"
    assert result.points == [
        TelemetryHistoryPoint(timestamp="2026-01-01T00:00:00Z", value=0.5)
    ]
    history.assert_awaited_once_with("mower-1", "accel_x", "cursor-1", ANY)

    monkeypatch.setattr(mower, "verify_ownership", AsyncMock(return_value=False))
    with pytest.raises(OwnershipError):
        await mower.get_telemetry_history_service(
            "user-1", "mower-1", "accel_x", None, object()
        )


async def test_get_mower_data_service_rejects_unowned_mower(monkeypatch):
    monkeypatch.setattr(mower, "get_mower_data", AsyncMock(return_value=[]))

    with pytest.raises(MowerNotFoundError):
        await mower.get_mower_data_service("user-1", "mower-1", object())


async def test_update_mower_name_service_validates_then_delegates(monkeypatch):
    verify = AsyncMock(return_value=True)
    update = AsyncMock()
    monkeypatch.setattr(mower, "verify_ownership", verify)
    monkeypatch.setattr(mower, "update_mower_name", update)

    await mower.update_mower_name_service("user-1", "mower-1", "NewName", object())

    update.assert_awaited_once()
    with pytest.raises(ValidationError):
        await mower.update_mower_name_service(
            "user-1", "mower-1", "not valid", object()
        )
    monkeypatch.setattr(mower, "verify_ownership", AsyncMock(return_value=False))
    with pytest.raises(OwnershipError):
        await mower.update_mower_name_service("user-1", "mower-1", "Valid", object())


async def test_update_mower_ownership_requires_actual_owner_match(monkeypatch):
    add = AsyncMock()
    monkeypatch.setattr(mower, "add_mower_to_user", add)
    monkeypatch.setattr(
        mower, "check_mower_ownership", AsyncMock(return_value="owner-1")
    )

    with pytest.raises(OwnershipError):
        await mower.update_mower_ownership_service(
            "wrong", "owner-2", "mower-1", object()
        )

    await mower.update_mower_ownership_service(
        "owner-1", "owner-2", "mower-1", object()
    )
    add.assert_awaited_once()


async def test_update_mower_ownership_assigns_unowned_mower(monkeypatch):
    add = AsyncMock()
    monkeypatch.setattr(mower, "add_mower_to_user", add)
    monkeypatch.setattr(mower, "check_mower_ownership", AsyncMock(return_value=None))

    await mower.update_mower_ownership_service(None, "new-owner", "mower-1", object())

    add.assert_awaited_once()
