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
    EmergencyStopCommand,
    ImuTelemetry,
    MowerCertificateRenewChallengeRequest,
    MowerCertificateRenewCompleteRequest,
    MowerCommandResponse,
    SetModeCommand,
    TelemetryList,
    TelemetryRecord,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ASYNCAPI_PATH = REPOSITORY_ROOT / "backend" / "zenoh_asyncapi.yaml"
APP_TYPES_PATH = REPOSITORY_ROOT / "app" / "src" / "generated" / "zenoh.ts"
RUST_TYPES_PATH = (
    REPOSITORY_ROOT
    / "nvidia_jetson"
    / "ros_ws"
    / "src"
    / "emi_mower_zenoh_gateway"
    / "src"
    / "generated"
    / "zenoh.rs"
)
RUST_PATHS_PATH = RUST_TYPES_PATH.with_name("zenoh_paths.rs")


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


def _rust_struct_properties(name: str) -> set[str]:
    source = RUST_TYPES_PATH.read_text()
    block = source.split(f"pub struct {name} {{\n", 1)[1].split("\n}", 1)[0]
    return set(re.findall(r"^    pub ([a-z_]+):", block, re.MULTILINE))


def test_telemetry_models_match_the_asyncapi_schema_in_all_consumers():
    """A telemetry field cannot be added to only one generated consumer model."""
    models = (("ImuTelemetry", ImuTelemetry), ("TelemetryRecord", TelemetryRecord))
    for name, model in models:
        fields = _schema_properties(name)
        assert fields == set(model.model_fields)
        assert fields == _typescript_interface_properties(name)
        assert fields == _rust_struct_properties(name)

    telemetry_list = _schema_block("TelemetryList")
    assert "items: {$ref: '#/components/schemas/TelemetryRecord'}" in telemetry_list
    assert TelemetryList.model_fields["root"].annotation == list[TelemetryRecord]
    app_types = APP_TYPES_PATH.read_text()
    assert "export type TelemetryList = TelemetryRecord[];" in app_types
    assert "pub type TelemetryList = Vec<TelemetryRecord>;" in RUST_TYPES_PATH.read_text()


def test_rust_gateway_routes_and_joystick_type_are_generated_from_asyncapi():
    assert _schema_properties("JoystickCommand") == _rust_struct_properties("JoystickCommand")
    rust_paths = RUST_PATHS_PATH.read_text()
    assert 'MOWER_JOYSTICK_ADDRESS: &str = "mower/{mower_id}/joystick"' in rust_paths
    assert 'MOWER_TELEMETRY_ADDRESS: &str = "mower/{mower_id}/telemetry"' in rust_paths


def test_certificate_renewal_contract_is_generated_for_backend_and_gateway():
    assert MowerCertificateRenewChallengeRequest().model_dump() == {}
    assert MowerCertificateRenewCompleteRequest.model_fields.keys() == {
        "nonce",
        "csr_pem",
        "tpm_signature",
    }
    source = RUST_TYPES_PATH.read_text()
    paths = RUST_PATHS_PATH.read_text()
    app_types = APP_TYPES_PATH.read_text()
    assert "pub struct MowerCertificateRenewCompleteRequest" in source
    assert "export interface MowerCertificateRenewCompleteRequest" in app_types
    assert (
        'MOWER_CERTIFICATE_RENEW_CHALLENGE_ADDRESS: &str =\n'
        '    "bootstrap/mower/{mower_id}/certificate/renew/challenge"'
    ) in paths


def test_telemetry_channel_references_the_shared_telemetry_list_message():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerTelemetry:\n", 1)[1].split("operations:\n", 1)[0]
    assert "address: mower/{mower_id}/telemetry" in channel
    assert "telemetryList: {$ref: '#/components/messages/TelemetryList'}" in channel


def test_mower_command_contract_is_typed_and_has_an_acceptance_reply():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerCommand:\n", 1)[1].split("  mowerTelemetryHistory:\n", 1)[0]
    assert "address: mower/{mower_id}/command" in channel
    assert "mowerCommandRequest: {$ref: '#/components/messages/MowerCommandRequest'}" in channel
    assert EmergencyStopCommand(command_id="command-1", type="emergency_stop").type == "emergency_stop"
    assert SetModeCommand(command_id="command-2", type="set_mode", mode="auto").mode == "auto"
    assert MowerCommandResponse(command_id="command-3", status="accepted").status == "accepted"


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
