"""Regression guards for the AsyncAPI telemetry contract.

The app and backend intentionally consume generated models from the same
``zenoh_asyncapi.yaml`` document.  These checks make a schema edit fail CI
until both generated outputs have been refreshed.
"""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.zenoh.generated import (
    ImuTelemetry,
    TelemetryList,
    TelemetryRecord,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ASYNCAPI_PATH = REPOSITORY_ROOT / "backend" / "zenoh_asyncapi.yaml"
APP_TYPES_PATH = REPOSITORY_ROOT / "app" / "src" / "generated" / "zenoh.ts"


def _schema_block(name: str) -> str:
    document = ASYNCAPI_PATH.read_text()
    schemas = document.split("  schemas:\n", 1)[1]
    match = re.search(
        rf"^    {name}:\n(?P<block>.*?)(?=^    [A-Z]|\Z)",
        schemas,
        re.MULTILINE | re.DOTALL,
    )
    assert match, f"Missing AsyncAPI schema: {name}"
    return match.group("block")


def _schema_properties(name: str) -> set[str]:
    block = _schema_block(name).split("      properties:\n", 1)[1]
    return set(re.findall(r"^        ([a-z_]+):", block, re.MULTILINE))


def _typescript_interface_properties(name: str) -> set[str]:
    source = APP_TYPES_PATH.read_text()
    block = source.split(f"export interface {name} {{\n", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r"^  ([a-z_]+)\??:", block, re.MULTILINE))


def test_telemetry_models_match_the_asyncapi_schema_in_both_services():
    """A telemetry field cannot be added to just the app or backend model."""
    models = (("ImuTelemetry", ImuTelemetry), ("TelemetryRecord", TelemetryRecord))
    for name, model in models:
        fields = _schema_properties(name)
        assert fields == set(model.model_fields)
        assert fields == _typescript_interface_properties(name)

    telemetry_list = _schema_block("TelemetryList")
    assert "items: {$ref: '#/components/schemas/TelemetryRecord'}" in telemetry_list
    assert TelemetryList.model_fields["root"].annotation == list[TelemetryRecord]
    app_types = APP_TYPES_PATH.read_text()
    assert "export type TelemetryList = TelemetryRecord[];" in app_types


def test_telemetry_channel_references_the_shared_telemetry_list_message():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerTelemetry:\n", 1)[1].split("operations:\n", 1)[0]
    assert "address: mower/{mower_id}/telemetry" in channel
    assert "telemetryList: {$ref: '#/components/messages/TelemetryList'}" in channel


def test_generated_telemetry_model_applies_asyncapi_defaults_and_direction_bounds():
    record = TelemetryRecord.model_validate(
        {
            "mower_id": "mower-1",
            "timestamp": "2026-08-16T12:00:00Z",
            "latitude": 40.7128,
            "longitude": -74.006,
            "battery_percentage": 81,
        }
    )

    assert record.left_motor_speed == 0
    assert record.left_motor_direction == 0
    assert record.slippage_detected is False

    with pytest.raises(ValidationError, match="left_motor_direction"):
        TelemetryRecord.model_validate(
            {**record.model_dump(mode="json"), "left_motor_direction": 2}
        )
