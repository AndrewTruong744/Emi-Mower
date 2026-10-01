"""Regression guards for the AsyncAPI telemetry contract.

The app and backend intentionally consume generated models from the same
``zenoh_asyncapi.yaml`` document.  These checks make a schema edit fail CI
until both generated outputs have been refreshed.
"""

import re
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from src.zenoh.generated import (
    CutoutUploadNotification,
    CutoutUploadUrlRequest,
    EmergencyStopCommand,
    ImuTelemetry,
    MowerCertificateRenewChallengeRequest,
    MowerCertificateRenewCompleteRequest,
    MowerCommandRequest,
    MowerCommandResponse,
    SetModeCommand,
    TelemetryHistoryResponse,
    TelemetryList,
    TelemetryRecord,
    UserData,
)
from src.zenoh.generated import types as generated_types

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ASYNCAPI_PATH = REPOSITORY_ROOT / "backend" / "zenoh_asyncapi.yaml"
APP_TYPES_PATH = REPOSITORY_ROOT / "app" / "src" / "generated" / "zenoh.ts"
APP_PATHS_PATH = APP_TYPES_PATH.with_name("zenohPaths.ts")
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
    schema = _schema_block(name)
    if "      properties:\n" not in schema:
        return set()
    block = schema.split("      properties:\n", 1)[1]
    return set(re.findall(r"^        ([a-z_]+):", block, re.MULTILINE))


def test_every_python_object_model_matches_schema_fields_and_requiredness():
    document = ASYNCAPI_PATH.read_text().split("  schemas:\n", 1)[1]
    names = re.findall(r"^    ([A-Za-z]\w+):\n", document, re.MULTILINE)
    for name in names:
        schema = _schema_block(name)
        if not re.search(r"^      type: object$", schema, re.MULTILINE):
            continue
        model = getattr(generated_types, name)
        assert set(model.model_fields) == _schema_properties(name), name
        required_match = re.search(
            r"^      required: \[([^]]*)\]", schema, re.MULTILINE
        )
        required = (
            {field.strip() for field in required_match.group(1).split(",")}
            if required_match
            else set()
        )
        assert {
            field for field, info in model.model_fields.items() if info.is_required()
        } == required, name
        assert model.model_config["extra"] == "allow", name


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
    assert (
        "pub type TelemetryList = Vec<TelemetryRecord>;" in RUST_TYPES_PATH.read_text()
    )


def test_rust_gateway_routes_and_joystick_type_are_generated_from_asyncapi():
    assert _schema_properties("JoystickCommand") == _rust_struct_properties(
        "JoystickCommand"
    )
    rust_paths = RUST_PATHS_PATH.read_text()
    assert 'MOWER_JOYSTICK_ADDRESS: &str = "mower/{mower_id}/joystick"' in rust_paths
    assert 'MOWER_TELEMETRY_ADDRESS: &str = "mower/{mower_id}/telemetry"' in rust_paths


def test_cutout_delivery_contract_is_generated_for_the_gateway():
    assert _schema_properties("MowerCutoutDelivery") == _rust_struct_properties(
        "MowerCutoutDelivery"
    )


def test_cutout_upload_contract_is_generated_for_backend_and_app():
    models = (
        ("CutoutUploadUrlRequest", CutoutUploadUrlRequest),
        ("CutoutUploadNotification", CutoutUploadNotification),
    )
    for name, model in models:
        fields = _schema_properties(name)
        assert fields == set(model.model_fields)
        assert fields == _typescript_interface_properties(name)
    rust_paths = RUST_PATHS_PATH.read_text()
    assert (
        'MOWER_CUTOUT_DELIVERY_ADDRESS: &str = "mower/{mower_id}/cutout/delivery"'
        in rust_paths
    )


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
        "MOWER_CERTIFICATE_RENEW_CHALLENGE_ADDRESS: &str =\n"
        '    "bootstrap/mower/{mower_id}/certificate/renew/challenge"'
    ) in paths


def test_telemetry_channel_references_the_shared_telemetry_list_message():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerTelemetry:\n", 1)[1].split("operations:\n", 1)[0]
    assert "address: mower/{mower_id}/telemetry" in channel
    assert "telemetryList: {$ref: '#/components/messages/TelemetryList'}" in channel


def test_liveliness_route_is_generated_for_the_app_and_gateway():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerLiveliness:\n", 1)[1].split(
        "  cutoutUploadUrl:\n", 1
    )[0]
    assert "address: mower/{mower_id}/liveliness" in channel
    assert "mowerLiveliness: {$ref: '#/components/messages/MowerLiveliness'}" in channel

    app_paths = APP_PATHS_PATH.read_text()
    rust_paths = RUST_PATHS_PATH.read_text()
    assert 'MOWER_LIVELINESS_ADDRESS = "mower/{mower_id}/liveliness"' in app_paths
    assert (
        'MOWER_LIVELINESS_ADDRESS: &str = "mower/{mower_id}/liveliness"' in rust_paths
    )


def test_mower_command_contract_is_typed_and_has_an_acceptance_reply():
    document = ASYNCAPI_PATH.read_text()
    channel = document.split("  mowerCommand:\n", 1)[1].split(
        "  mowerTelemetryHistory:\n", 1
    )[0]
    assert "address: mower/{mower_id}/command" in channel
    assert (
        "mowerCommandRequest: {$ref: '#/components/messages/MowerCommandRequest'}"
        in channel
    )
    assert (
        EmergencyStopCommand(command_id="command-1", type="emergency_stop").type
        == "emergency_stop"
    )
    assert (
        SetModeCommand(command_id="command-2", type="set_mode", mode="auto").mode
        == "auto"
    )
    assert (
        MowerCommandResponse(command_id="command-3", status="accepted").status
        == "accepted"
    )


def test_top_level_array_and_command_union_validate_the_declared_payload_shapes():
    telemetry_schema = _schema_block("TelemetryList")
    assert "type: array" in telemetry_schema
    assert "items: {$ref: '#/components/schemas/TelemetryRecord'}" in telemetry_schema
    telemetry = {
        "mower_id": "mower-1",
        "timestamp": "2026-08-16T12:00:00Z",
        "latitude": 40.7128,
        "longitude": -74.006,
        "battery_percentage": 81,
    }
    assert len(TelemetryList.model_validate([telemetry]).root) == 1
    with pytest.raises(ValidationError):
        TelemetryList.model_validate({"records": [telemetry]})

    command_schema = _schema_block("MowerCommandRequest")
    assert command_schema.count("#/components/schemas/") == 3
    command_adapter = TypeAdapter(MowerCommandRequest)
    assert (
        command_adapter.validate_python(
            {"command_id": "command-1", "type": "set_power", "enabled": True}
        ).type
        == "set_power"
    )
    with pytest.raises(ValidationError):
        command_adapter.validate_python(
            {"command_id": "command-1", "type": "set_power"}
        )


def test_generated_telemetry_model_keeps_defaults_and_protocol_choices():
    record = TelemetryRecord.model_validate(
        {
            "mower_id": "mower-1",
            "timestamp": "2026-08-16T12:00:00Z",
            "latitude": 40.7128,
            "longitude": -74.006,
            "battery_percentage": 81,
        }
    )
    assert record.left_motor_speed == 0.0
    assert record.left_motor_direction == 0
    assert record.slippage_detected is False
    with pytest.raises(ValidationError, match="left_motor_direction"):
        TelemetryRecord.model_validate(
            {**record.model_dump(mode="json"), "left_motor_direction": 2}
        )


def test_nullable_fields_and_open_objects_follow_wire_shapes():
    response = {
        "telemetry_type": "battery_percentage",
        "limit": 60,
        "total": 0,
        "has_more": False,
        "next_cursor": None,
        "points": [],
    }
    assert TelemetryHistoryResponse.model_validate(response).next_cursor is None
    with pytest.raises(ValidationError, match="next_cursor"):
        TelemetryHistoryResponse.model_validate(
            {
                field: value
                for field, value in response.items()
                if field != "next_cursor"
            }
        )

    command = MowerCommandResponse(command_id="command-1", status="accepted")
    assert command.reason is None
    user = {"id": "user-1", "email": "user@example.com", "name": "User", "mowers": []}
    assert UserData.model_validate({**user, "custom": 1}).model_dump()["custom"] == 1
    with pytest.raises(ValidationError, match="mowers"):
        UserData.model_validate(
            {field: value for field, value in user.items() if field != "mowers"}
        )
