"""Coordinate reliable draining of buffered mower telemetry."""

import logging

from src.config.database import AsyncSessionLocal
from src.repositories.telemetry import (
    claim_active_telemetry_buffer,
    delete_telemetry_buffer,
    list_active_telemetry_buffers,
    list_temporary_telemetry_buffers,
    persist_telemetry_records,
    read_telemetry_buffer,
)
from src.zenoh.generated import TelemetryRecord

logger = logging.getLogger("services.telemetry_buffer")


async def persist_telemetry_buffer(temp_key: str) -> None:
    """Persist one temporary telemetry list and delete it only on success."""
    logger.info("Processing temporary key: %s", temp_key)
    items = await read_telemetry_buffer(temp_key)
    if not items:
        await delete_telemetry_buffer(temp_key)
        return

    logger.info("Found %d telemetry entries in %s", len(items), temp_key)
    telemetry_records: list[TelemetryRecord] = []
    for item in items:
        try:
            telemetry_records.append(TelemetryRecord.model_validate_json(item))
        except Exception:
            logger.error("Failed to validate telemetry item. Skipping.", exc_info=True)

    if not telemetry_records:
        await delete_telemetry_buffer(temp_key)
        return

    try:
        async with AsyncSessionLocal() as session:
            inserted_count = await persist_telemetry_records(telemetry_records, session)
        logger.info(
            "Successfully saved %d telemetry records to Postgres.", inserted_count
        )
        await delete_telemetry_buffer(temp_key)
        logger.info("Cleaned up Valkey temp key: %s", temp_key)
    except Exception:
        logger.error(
            "Database error saving telemetry from key %s. Keeping key for retry.",
            temp_key,
            exc_info=True,
        )


async def flush_pending_telemetry_buffers() -> None:
    """Atomically drain active telemetry lists and retry interrupted batches."""
    try:
        temp_keys = await list_temporary_telemetry_buffers()
        if temp_keys:
            logger.info("Found %d leftover temp keys to process.", len(temp_keys))
            for temp_key in temp_keys:
                await persist_telemetry_buffer(temp_key)

        active_keys = await list_active_telemetry_buffers()
        if not active_keys:
            logger.info("No new telemetry data found in Valkey.")
            return

        logger.info("Found %d active telemetry lists in Valkey.", len(active_keys))
        for key in active_keys:
            try:
                temp_key = await claim_active_telemetry_buffer(key)
            except Exception:
                logger.error("Failed to claim telemetry buffer %s.", key, exc_info=True)
                continue

            await persist_telemetry_buffer(temp_key)
    except Exception:
        logger.error("Error flushing telemetry buffers.", exc_info=True)
