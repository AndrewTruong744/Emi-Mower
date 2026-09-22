"""Repository operations for buffered mower telemetry."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.models.mower import MowerImuModel, MowerTelemetryModel
from src.schemas.valkey import (
    MOWER_TELEMETRY_PATTERN,
    MOWER_TELEMETRY_TEMP_PATTERN,
    mower_id_from_telemetry_key,
    mower_telemetry_key,
    mower_telemetry_temp_key,
)
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


async def list_temporary_telemetry_buffers() -> list[str]:
    """Return temporary telemetry-buffer keys left by interrupted drains."""
    return await _telemetry_keys(MOWER_TELEMETRY_TEMP_PATTERN)


async def list_active_telemetry_buffers() -> list[str]:
    """Return active telemetry-buffer keys awaiting a worker drain."""
    return await _telemetry_keys(MOWER_TELEMETRY_PATTERN)


async def _telemetry_keys(pattern: str) -> list[str]:
    try:
        async with get_valkey_client() as client:
            return await client.keys(pattern)
    except Exception as error:
        logger.error("Failed to list telemetry buffers", exc_info=True)
        raise RepositoryError("Failed to list telemetry buffers") from error


async def claim_active_telemetry_buffer(active_key: str) -> str:
    """Atomically rename one active telemetry list to its retryable temp key."""
    try:
        temporary_key = mower_telemetry_temp_key(
            mower_id_from_telemetry_key(active_key)
        )
        async with get_valkey_client() as client:
            await client.rename(active_key, temporary_key)
        return temporary_key
    except Exception as error:
        logger.error("Failed to claim telemetry buffer %s", active_key, exc_info=True)
        raise RepositoryError("Failed to claim telemetry buffer") from error


async def read_telemetry_buffer(temporary_key: str) -> list[str]:
    """Read every serialized record from one claimed telemetry list."""
    try:
        async with get_valkey_client() as client:
            return await client.lrange(temporary_key, 0, -1)
    except Exception as error:
        logger.error("Failed to read telemetry buffer %s", temporary_key, exc_info=True)
        raise RepositoryError("Failed to read telemetry buffer") from error


async def delete_telemetry_buffer(temporary_key: str) -> None:
    """Delete a telemetry list after its records have been handled."""
    try:
        async with get_valkey_client() as client:
            await client.delete(temporary_key)
    except Exception as error:
        logger.error(
            "Failed to delete telemetry buffer %s", temporary_key, exc_info=True
        )
        raise RepositoryError("Failed to delete telemetry buffer") from error


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
            **record.model_dump(exclude={"mower_id", "imu_data"}),
        )

        if record.imu_data is not None:
            telemetry.imu_data = MowerImuModel(**record.imu_data.model_dump())

        models.append(telemetry)

    return models


async def persist_telemetry_records(
    telemetry_data: list[TelemetryRecord], db: AsyncSession
) -> int:
    """Persist telemetry records and return the number inserted."""
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
