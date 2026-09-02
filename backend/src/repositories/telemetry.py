"""Repository operations for buffered mower telemetry."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerImuModel, MowerTelemetryModel
from src.schemas.valkey import mower_telemetry_key
from src.zenoh.generated import TelemetryRecord

logger = logging.getLogger("repositories.telemetry")


async def add_telemetry_to_cache(
    telemetry_data: list[TelemetryRecord],
) -> int:
    """Append telemetry records to their mower-specific Valkey lists."""
    if not telemetry_data:
        return 0

    records_by_mower: dict[str, list[str]] = {}
    for record in telemetry_data:
        records_by_mower.setdefault(record.mower_id, []).append(
            record.model_dump_json()
        )

    try:
        async with get_valkey_client() as client:
            for mower_id, records in records_by_mower.items():
                await client.rpush(mower_telemetry_key(mower_id), *records)
    except Exception as err:
        logger.error("Failed to cache telemetry data", exc_info=True)
        raise RepositoryError("Failed to cache telemetry data") from err

    return len(telemetry_data)


def _build_telemetry_models(
    telemetry_data: list[TelemetryRecord],
) -> list[MowerTelemetryModel]:
    models: list[MowerTelemetryModel] = []
    for record in telemetry_data:
        try:
            mower_id = uuid.UUID(record.mower_id)
        except (AttributeError, ValueError):
            logger.warning(
                "Skipping telemetry with invalid mower UUID %s", record.mower_id
            )
            continue

        telemetry = MowerTelemetryModel(
            mower_id=mower_id,
            timestamp=record.timestamp,
            latitude=record.latitude,
            longitude=record.longitude,
            battery_percentage=record.battery_percentage,
            left_motor_speed=record.left_motor_speed,
            left_motor_direction=record.left_motor_direction,
            right_motor_speed=record.right_motor_speed,
            right_motor_direction=record.right_motor_direction,
            cutting_motor_speed=record.cutting_motor_speed,
            slippage_detected=record.slippage_detected,
        )

        if record.imu_data is not None:
            telemetry.imu_data = MowerImuModel(
                accel_x=record.imu_data.accel_x,
                accel_y=record.imu_data.accel_y,
                accel_z=record.imu_data.accel_z,
                gyro_x=record.imu_data.gyro_x,
                gyro_y=record.imu_data.gyro_y,
                gyro_z=record.imu_data.gyro_z,
                mag_x=record.imu_data.mag_x,
                mag_y=record.imu_data.mag_y,
                mag_z=record.imu_data.mag_z,
            )

        models.append(telemetry)

    return models


async def push_cached_telemetry_to_db(
    telemetry_data: list[TelemetryRecord], db: AsyncSession
) -> int:
    """Persist cached telemetry records and return the number inserted."""
    telemetry_models = _build_telemetry_models(telemetry_data)
    if not telemetry_models:
        return 0

    try:
        db.add_all(telemetry_models)
        await db.commit()
    except Exception as err:
        await db.rollback()
        logger.error("Failed to persist cached telemetry", exc_info=True)
        raise RepositoryError("Failed to persist cached telemetry") from err

    return len(telemetry_models)
