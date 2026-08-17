"""Cursor-paged graph telemetry reads from PostgreSQL."""

import base64
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import RepositoryError, ValidationError
from src.models.mower import MowerImuModel, MowerTelemetryModel

TELEMETRY_PAGE_SIZE = 60
TELEMETRY_COLUMNS = {
    "battery_percentage": MowerTelemetryModel.battery_percentage,
    "left_motor_speed": MowerTelemetryModel.left_motor_speed,
    "right_motor_speed": MowerTelemetryModel.right_motor_speed,
    "cutting_motor_speed": MowerTelemetryModel.cutting_motor_speed,
    "slippage_detected": MowerTelemetryModel.slippage_detected,
    "accel_x": MowerImuModel.accel_x,
    "accel_y": MowerImuModel.accel_y,
    "accel_z": MowerImuModel.accel_z,
    "gyro_x": MowerImuModel.gyro_x,
    "gyro_y": MowerImuModel.gyro_y,
    "gyro_z": MowerImuModel.gyro_z,
    "mag_x": MowerImuModel.mag_x,
    "mag_y": MowerImuModel.mag_y,
    "mag_z": MowerImuModel.mag_z,
}


def _mower_uuid(mower_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(mower_id)
    except (TypeError, ValueError) as error:
        raise ValidationError("Mower ID must be a UUID") from error


def encode_telemetry_cursor(timestamp: datetime, telemetry_id: uuid.UUID) -> str:
    """Create an opaque ordering cursor from the final record in a page."""
    value = json.dumps({"timestamp": timestamp.isoformat(), "id": str(telemetry_id)})
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_telemetry_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode and validate a cursor without a client-controlled offset."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value: dict[str, Any] = json.loads(base64.urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(value["timestamp"]), uuid.UUID(value["id"])
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ValidationError("Invalid telemetry cursor") from error


async def get_telemetry_history(
    mower_id: str, telemetry_type: str, cursor: str | None, db: AsyncSession
) -> tuple[int, list[tuple], str | None]:
    """Return a stable newest-first graph page and an opaque next cursor.

    The cursor pairs timestamp with primary key, so records that share a
    timestamp are still traversed exactly once while newer telemetry arrives.
    """
    column = TELEMETRY_COLUMNS.get(telemetry_type)
    if column is None:
        raise ValidationError("Unsupported telemetry graph type")

    mower_uuid = _mower_uuid(mower_id)
    filters = (
        MowerTelemetryModel.mower_id == mower_uuid,
        column.is_not(None),
    )
    statement = (
        select(
            MowerTelemetryModel.timestamp,
            column.label("value"),
            MowerTelemetryModel.id,
        )
        .outerjoin(MowerImuModel)
        .where(*filters)
        .order_by(desc(MowerTelemetryModel.timestamp), desc(MowerTelemetryModel.id))
        .limit(TELEMETRY_PAGE_SIZE + 1)
    )
    if cursor:
        timestamp, telemetry_id = decode_telemetry_cursor(cursor)
        statement = statement.where(
            or_(
                MowerTelemetryModel.timestamp < timestamp,
                and_(
                    MowerTelemetryModel.timestamp == timestamp,
                    MowerTelemetryModel.id < telemetry_id,
                ),
            )
        )

    try:
        total = await db.scalar(
            select(func.count())
            .select_from(MowerTelemetryModel)
            .outerjoin(MowerImuModel)
            .where(*filters)
        )
        results = (await db.execute(statement)).all()
    except Exception as error:
        raise RepositoryError("Failed to read mower telemetry history") from error

    has_more = len(results) > TELEMETRY_PAGE_SIZE
    points = results[:TELEMETRY_PAGE_SIZE]
    next_cursor = (
        encode_telemetry_cursor(points[-1].timestamp, points[-1].id)
        if has_more and points
        else None
    )
    return total or 0, points, next_cursor
