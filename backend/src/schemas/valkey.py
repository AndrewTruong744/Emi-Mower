"""Schemas and key definitions for the Valkey cache.

Valkey values are stored as JSON strings unless noted otherwise.  The cache
uses a cache-aside strategy, so all entries have the same default lifetime and
callers refresh that lifetime when a cached value is read.
"""

from datetime import datetime

from pydantic import BaseModel, RootModel

# Cache entries are written with ``setex`` throughout the repositories.
VALKEY_CACHE_TTL_SECONDS = 86_400

# Key templates are kept here so new repository code does not have to repeat
# the cache contract.  Values in braces are identifiers supplied by callers.
USER_MOWERS_KEY = "user:{user_id}:mowers"
USER_DATA_KEY = "user:{user_id}:data"
MOWER_DATA_KEY = "mower:{mower_id}:data"
MOWER_STATUS_KEY = "mower:{mower_id}:status"
MOWER_OWNER_KEY = "mower:{mower_id}:owner"
ZENOH_TOKEN_EXPIRY_KEY = "user:zenoh_tokens"

# The telemetry worker uses a Valkey LIST at this key and temporarily renames
# it to the same key with ``:temp`` appended while it uploads the records.
MOWER_TELEMETRY_KEY = "mower:{mower_id}:telemetry:data"
MOWER_TELEMETRY_TEMP_KEY = "mower:{mower_id}:telemetry:data:temp"
MOWER_TELEMETRY_PATTERN = "mower:*:telemetry:data"
MOWER_TELEMETRY_TEMP_PATTERN = "mower:*:telemetry:data:temp"


def user_mowers_key(user_id: str) -> str:
    """Return the key containing a user's JSON list of mower IDs."""

    return USER_MOWERS_KEY.format(user_id=user_id)


def user_data_key(user_id: str) -> str:
    """Return the key containing a user's JSON-serialized data."""

    return USER_DATA_KEY.format(user_id=user_id)


def mower_data_key(mower_id: str) -> str:
    """Return the key containing a mower's JSON-serialized data."""

    return MOWER_DATA_KEY.format(mower_id=mower_id)


def mower_status_key(mower_id: str) -> str:
    """Return the key containing a mower's plain-text status."""

    return MOWER_STATUS_KEY.format(mower_id=mower_id)


def mower_owner_key(mower_id: str) -> str:
    """Return the key containing a mower owner ID or the ``dne`` marker."""

    return MOWER_OWNER_KEY.format(mower_id=mower_id)


def mower_telemetry_key(mower_id: str) -> str:
    """Return the telemetry LIST key used by the upload worker."""

    return MOWER_TELEMETRY_KEY.format(mower_id=mower_id)


def mower_telemetry_temp_key(mower_id: str) -> str:
    """Return the temporary telemetry LIST key used during upload."""

    return MOWER_TELEMETRY_TEMP_KEY.format(mower_id=mower_id)


class UserMowersCache(RootModel[list[str]]):
    """JSON value for ``user:{user_id}:mowers``."""


class UserDataCache(BaseModel):
    """JSON value for ``user:{user_id}:data``."""

    id: str
    email: str
    name: str
    created_at: datetime | None = None


class MowerDataCache(BaseModel):
    """JSON value for ``mower:{mower_id}:data``.

    ``status`` is deliberately not included: repository code stores it under
    the separate ``mower:{mower_id}:status`` key and combines it on reads.
    """

    id: str
    serial_number: str
    nickname: str
    owner_id: str | None = None


class MowerOwnerCache(RootModel[str]):
    """Plain-string value for ``mower:{mower_id}:owner``.

    A missing owner is represented by the literal ``"dne"`` marker.
    """


class MowerStatusCache(RootModel[str]):
    """Plain-string value for ``mower:{mower_id}:status``."""


class ImuTelemetryCache(BaseModel):
    """Nested IMU data in a telemetry record."""

    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    mag_x: float
    mag_y: float
    mag_z: float


class TelemetryRecordCache(BaseModel):
    """JSON item stored in the mower telemetry LIST.

    The telemetry worker reads these fields before creating the corresponding
    PostgreSQL telemetry and IMU records.
    """

    mower_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    battery_percentage: int
    left_motor_speed: float = 0.0
    left_motor_direction: int = 0
    right_motor_speed: float = 0.0
    right_motor_direction: int = 0
    cutting_motor_speed: float = 0.0
    slippage_detected: bool = False
    rgb_image_url: str | None = None
    lidar_image_url: str | None = None
    imu_data: ImuTelemetryCache | None = None


class TelemetryListCache(RootModel[list[TelemetryRecordCache]]):
    """Logical schema for the records in a mower telemetry LIST."""
