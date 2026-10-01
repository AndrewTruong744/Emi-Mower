"""Generated from ``backend/zenoh_asyncapi.yaml``. Do not edit manually.

Regenerate with ``npm --prefix tools run generate``.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, RootModel


class ZenohModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class UserLoginRequest(ZenohModel):
    id_token: str


class AddMowerToUserRequest(ZenohModel):
    id_token: str
    mower_id: str


class AddMowerToUserResponse(ZenohModel):
    message: str
    user_id: str
    mower_id: str


class UpdateUserNameRequest(ZenohModel):
    id_token: str
    new_user_name: str


class UpdateUserNameResponse(ZenohModel):
    message: str
    user_id: str
    new_user_name: str


class UpdateMowerNameRequest(ZenohModel):
    id_token: str
    new_name: str


class UpdateMowerNameResponse(ZenohModel):
    message: str
    mower_id: str
    new_name: str


class UpdateUserEmailRequest(ZenohModel):
    id_token: str
    new_id_token: str


class UpdateUserEmailResponse(ZenohModel):
    message: str
    user_id: str
    new_email: str


class UserData(ZenohModel):
    id: str
    email: str
    name: str
    created_at: str | None = None
    mowers: list[str]


class UserLoginResponse(ZenohModel):
    user_id: str
    token: str
    expires_in: int
    user_data: UserData


class LiveKitConsumeRequest(ZenohModel):
    pass


class LiveKitUploadRequest(ZenohModel):
    pass


class LiveKitTokenResponse(ZenohModel):
    token: str
    url: str
    expires_in: int


class JoystickCommand(ZenohModel):
    x: float
    y: float


class EmergencyStopCommand(ZenohModel):
    command_id: str
    type: Literal["emergency_stop"]


class SetPowerCommand(ZenohModel):
    command_id: str
    type: Literal["set_power"]
    enabled: bool


class SetModeCommand(ZenohModel):
    command_id: str
    type: Literal["set_mode"]
    mode: Literal["manual", "auto"]


MowerCommandRequest = EmergencyStopCommand | SetPowerCommand | SetModeCommand


class MowerCommandResponse(ZenohModel):
    command_id: str
    status: Literal["accepted", "rejected"]
    reason: str | None = None


class TelemetryHistoryRequest(ZenohModel):
    id_token: str
    cursor: str | None = None


class TelemetryHistoryPoint(ZenohModel):
    timestamp: str
    value: float


class TelemetryHistoryResponse(ZenohModel):
    telemetry_type: str
    limit: int
    total: int
    has_more: bool
    next_cursor: str | None
    points: list[TelemetryHistoryPoint]


class ImuTelemetry(ZenohModel):
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    mag_x: float
    mag_y: float
    mag_z: float


class TelemetryRecord(ZenohModel):
    mower_id: str
    timestamp: str
    latitude: float
    longitude: float
    battery_percentage: int
    left_motor_speed: float = 0.0
    left_motor_direction: Literal[-1, 0, 1] = 0
    right_motor_speed: float = 0.0
    right_motor_direction: Literal[-1, 0, 1] = 0
    cutting_motor_speed: float = 0.0
    slippage_detected: bool = False
    imu_data: ImuTelemetry | None = None


class TelemetryList(RootModel[list[TelemetryRecord]]):
    pass


class MowerLiveliness(ZenohModel):
    pass


class CutoutUploadUrlRequest(ZenohModel):
    id_token: str
    content_type: Literal["image/png", "image/jpeg", "image/webp"]


class CutoutUploadUrlResponse(ZenohModel):
    cutout_id: str
    upload_url: str
    expires_in: int
    object_key: str
    content_type: str


class CutoutUploadNotification(ZenohModel):
    id_token: str
    cutout_id: str
    object_key: str
    content_type: Literal["image/png", "image/jpeg", "image/webp"]
    success: bool
    failure_reason: str | None = None


class MowerCutoutDelivery(ZenohModel):
    cutout_id: str
    download_url: str
    expires_in: int
    content_type: str


class MowerCertificateRenewChallengeRequest(ZenohModel):
    pass


class MowerCertificateRenewChallengeResponse(ZenohModel):
    nonce: str
    expires_in: int


class MowerCertificateRenewCompleteRequest(ZenohModel):
    nonce: str
    csr_pem: str
    tpm_signature: str


class MowerCertificateRenewCompleteResponse(ZenohModel):
    certificate_pem: str
    ca_chain_pem: str
    expires_at: str


class ProblemDetails(ZenohModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    timestamp: str
