from importlib import import_module
from unittest.mock import AsyncMock, Mock

from src.zenoh.generated import TelemetryList
from src.zenoh.listeners import MOWER_TELEMETRY_KEY_EXPR, mower_telemetry


async def test_mower_telemetry_listener_buffers_the_payload(monkeypatch):
    listener = import_module("src.zenoh.listeners.mower_telemetry")

    service = AsyncMock()
    monkeypatch.setattr(listener, "add_telemetry_data_service", service)
    payload = TelemetryList(
        [
            {
                "mower_id": "mower-1",
                "timestamp": "2026-01-01T00:00:00Z",
                "latitude": 1,
                "longitude": 2,
                "battery_percentage": 90,
            }
        ]
    )

    result = await mower_telemetry(payload, Mock())

    assert result is None
    service.assert_awaited_once_with(payload.root)
    assert MOWER_TELEMETRY_KEY_EXPR == "mower/*/telemetry"
