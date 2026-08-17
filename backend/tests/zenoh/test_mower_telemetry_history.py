from importlib import import_module
from unittest.mock import ANY, AsyncMock, Mock

import pytest

from src.exceptions import ValidationError
from src.zenoh.generated import TelemetryHistoryRequest, TelemetryHistoryResponse
from src.zenoh.listeners.mower_telemetry_history import (
    MOWER_TELEMETRY_HISTORY_KEY_EXPR,
    _telemetry_path_from_query_key,
    mower_telemetry_history,
)


def test_telemetry_history_key_and_path_are_specific_to_one_graph_metric():
    assert MOWER_TELEMETRY_HISTORY_KEY_EXPR == "mower/*/telemetry/*/old"
    assert _telemetry_path_from_query_key("mower/mower-1/telemetry/accel_x/old") == (
        "mower-1",
        "accel_x",
    )
    with pytest.raises(ValidationError):
        _telemetry_path_from_query_key("mower/mower-1/telemetry/accel_x")


async def test_telemetry_history_verifies_firebase_token_then_reads_owned_history(
    monkeypatch,
):
    listener = import_module("src.zenoh.listeners.mower_telemetry_history")

    verify = AsyncMock(return_value={"uid": "user-1"})
    service = AsyncMock(
        return_value=TelemetryHistoryResponse(
            telemetry_type="accel_x",
            limit=60,
            total=180,
            has_more=True,
            next_cursor="next-page",
            points=[],
        )
    )
    monkeypatch.setattr(listener, "verify_zenoh_google_id_token", verify)
    monkeypatch.setattr(listener, "get_telemetry_history_service", service)

    result = await mower_telemetry_history(
        TelemetryHistoryRequest(id_token="firebase-token"),
        Mock(),
        "mower/mower-1/telemetry/accel_x/old",
    )

    verify.assert_awaited_once_with("firebase-token")
    service.assert_awaited_once_with("user-1", "mower-1", "accel_x", None, ANY)
    assert result.next_cursor == "next-page"
