from importlib import import_module
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from src.exceptions import ValidationError
from src.services.mower import mower_route_params
from src.zenoh.generated import TelemetryHistoryRequest, TelemetryHistoryResponse
from src.zenoh.listeners.mower_telemetry_history import (
    MOWER_TELEMETRY_HISTORY_KEY_EXPR,
    mower_telemetry_history,
)


def test_telemetry_history_key_and_path_are_specific_to_one_graph_metric():
    assert MOWER_TELEMETRY_HISTORY_KEY_EXPR == "mower/*/telemetry/*/old"
    assert mower_route_params(
        "mower/mower-1/telemetry/accel_x/old", MOWER_TELEMETRY_HISTORY_KEY_EXPR
    ) == ("mower-1", "accel_x")
    with pytest.raises(ValidationError):
        mower_route_params(
            "mower/mower-1/telemetry/accel_x", MOWER_TELEMETRY_HISTORY_KEY_EXPR
        )


async def test_telemetry_history_verifies_firebase_token_then_reads_owned_history(
    monkeypatch,
):
    listener = import_module("src.zenoh.listeners.mower_telemetry_history")

    verify = AsyncMock(return_value={"user_id": "user-1"})
    service = AsyncMock(
        return_value={
            "telemetry_type": "accel_x",
            "limit": 60,
            "total": 180,
            "next_cursor": "next-page",
            "points": [("2026-01-01T00:00:00Z", 0.5)],
        }
    )
    monkeypatch.setattr(listener, "verify_firebase_id_token", verify)
    monkeypatch.setattr(listener, "get_telemetry_history_service", service)

    result = await mower_telemetry_history(
        TelemetryHistoryRequest(id_token="firebase-token"),
        Mock(),
        "mower/mower-1/telemetry/accel_x/old",
    )

    verify.assert_awaited_once_with("firebase-token")
    service.assert_awaited_once_with("user-1", "mower-1", "accel_x", None, ANY)
    assert isinstance(result, TelemetryHistoryResponse)
    assert result.next_cursor == "next-page"
    assert result.has_more is True
    assert result.points[0].value == 0.5
