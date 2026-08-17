"""Generated from ``backend/zenoh_asyncapi.yaml``.

Do not edit manually. Regenerate with ``backend/scripts/generate_types.sh``.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, RootModel


class UserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str


class AddMowerToUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str
    mower_id: str


class AddMowerToUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    user_id: str
    mower_id: str


class UpdateUserNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str
    new_user_name: str


class UpdateUserNameResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    user_id: str
    new_user_name: str


class UpdateMowerNameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str
    new_name: str


class UpdateMowerNameResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    mower_id: str
    new_name: str


class UpdateUserEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str
    new_id_token: str


class UpdateUserEmailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    user_id: str
    new_email: str


class UserData(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    email: str
    name: str
    created_at: datetime | None = None
    mowers: list[str] = []


class UserLoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    token: str
    expires_in: int
    user_data: UserData


class LiveKitConsumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LiveKitUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LiveKitTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    url: str
    expires_in: int


class JoystickCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float


class TelemetryHistoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str
    cursor: str | None = None


class TelemetryHistoryPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    value: float


class TelemetryHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telemetry_type: str
    limit: int
    total: int
    has_more: bool
    next_cursor: str | None = None
    points: list[TelemetryHistoryPoint]


class ImuTelemetry(BaseModel):
    """Generated from ``components.schemas.ImuTelemetry``."""

    model_config = ConfigDict(extra="forbid")

    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    mag_x: float
    mag_y: float
    mag_z: float


class TelemetryRecord(BaseModel):
    """Generated from ``components.schemas.TelemetryRecord``."""

    model_config = ConfigDict(extra="forbid")

    mower_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    battery_percentage: int
    left_motor_speed: float = 0.0
    left_motor_direction: Literal[-1, 0, 1] = 0
    right_motor_speed: float = 0.0
    right_motor_direction: Literal[-1, 0, 1] = 0
    cutting_motor_speed: float = 0.0
    slippage_detected: bool = False
    rgb_image_url: str | None = None
    lidar_image_url: str | None = None
    imu_data: ImuTelemetry | None = None


class TelemetryList(RootModel[list[TelemetryRecord]]):
    """Generated from ``components.schemas.TelemetryList``."""


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    timestamp: datetime


WireMessage = (
    UserLoginRequest
    | UserLoginResponse
    | AddMowerToUserRequest
    | AddMowerToUserResponse
    | UpdateUserNameRequest
    | UpdateUserNameResponse
    | UpdateMowerNameRequest
    | UpdateMowerNameResponse
    | UpdateUserEmailRequest
    | UpdateUserEmailResponse
    | LiveKitConsumeRequest
    | LiveKitUploadRequest
    | LiveKitTokenResponse
    | JoystickCommand
    | TelemetryHistoryRequest
    | TelemetryHistoryResponse
    | ProblemDetails
    | dict[str, Any]
)
