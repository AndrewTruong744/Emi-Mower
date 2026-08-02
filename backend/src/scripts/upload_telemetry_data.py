import asyncio
import logging
import sys
import uuid

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerImuModel, MowerTelemetryModel
from src.schemas.valkey import (
    MOWER_TELEMETRY_PATTERN,
    MOWER_TELEMETRY_TEMP_PATTERN,
    TelemetryRecordCache,
    mower_telemetry_temp_key,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("upload_telemetry_worker")


async def process_key(v_client, temp_key: str) -> None:
    """
    Reads all items from a temporary Valkey list, parses them,
    saves them to PostgreSQL, and deletes the temporary list upon success.
    """
    logger.info(f"Processing temporary key: {temp_key}")
    items = await v_client.lrange(temp_key, 0, -1)
    if not items:
        # List is empty, clean it up
        await v_client.delete(temp_key)
        return

    logger.info(f"Found {len(items)} telemetry entries in {temp_key}")
    telemetry_records = []

    for item in items:
        try:
            record = TelemetryRecordCache.model_validate_json(item)
        except Exception as e:
            logger.error(f"Failed to validate telemetry item: {e}. Skipping.")
            continue

        try:
            mower_id = uuid.UUID(record.mower_id)
        except ValueError as e:
            logger.error(
                f"Invalid mower_uuid format '{record.mower_id}': {e}. Skipping."
            )
            continue

        telemetry_entry = MowerTelemetryModel(
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
            rgb_image_url=record.rgb_image_url,
            lidar_image_url=record.lidar_image_url,
        )

        # Parse nested IMU data if exists
        if record.imu_data is not None:
            imu_entry = MowerImuModel(
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
            telemetry_entry.imu_data = imu_entry

        telemetry_records.append(telemetry_entry)

    if not telemetry_records:
        # No valid records to save, just delete the temp key
        await v_client.delete(temp_key)
        return

    # Save all telemetry records in a database transaction
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                session.add_all(telemetry_records)
            await session.commit()
        logger.info(
            "Successfully saved %d telemetry records to Postgres.",
            len(telemetry_records),
        )

        # Clean up Valkey after successful Postgres transaction
        await v_client.delete(temp_key)
        logger.info(f"Cleaned up Valkey temp key: {temp_key}")
    except Exception as e:
        logger.error(
            "Database error saving telemetry from key %s: %s. Keeping key for retry.",
            temp_key,
            e,
            exc_info=True,
        )


async def run_sync_cycle() -> None:
    """
    Finds telemetry data lists in Valkey, renames them,
    processes the renamed lists, and deletes them.
    """
    v_client = get_valkey_client()
    try:
        # 1. First, check for and process any leftover temp keys (from crashed run)
        temp_keys = await v_client.keys(MOWER_TELEMETRY_TEMP_PATTERN)
        if temp_keys:
            logger.info(f"Found {len(temp_keys)} leftover temp keys to process.")
            for temp_key in temp_keys:
                await process_key(v_client, temp_key)

        # 2. Scan for active telemetry lists
        active_keys = await v_client.keys(MOWER_TELEMETRY_PATTERN)
        if not active_keys:
            logger.info("No new telemetry data found in Valkey.")
            return

        logger.info(f"Found {len(active_keys)} active telemetry lists in Valkey.")

        # 3. Rename active keys to temp keys and process them
        for key in active_keys:
            mower_id = key.split(":", 2)[1]
            temp_key = mower_telemetry_temp_key(mower_id)
            try:
                # Rename is atomic
                await v_client.rename(key, temp_key)
            except Exception as e:
                logger.error(f"Failed to rename key {key} to {temp_key}: {e}")
                continue

            await process_key(v_client, temp_key)

    except Exception as e:
        logger.error(f"Error in sync cycle: {e}", exc_info=True)


async def main():
    logger.info("Starting telemetry upload worker daemon...")
    while True:
        start_time = time.time()
        logger.info("Starting telemetry sync cycle...")
        await run_sync_cycle()
        logger.info("Telemetry sync cycle finished.")

        # Sleep for 60 seconds (adjusted for execution time to avoid drift)
        elapsed = time.time() - start_time
        sleep_duration = max(1.0, 60.0 - elapsed)
        logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
        await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    import time

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telemetry worker daemon stopped by user.")
    except Exception as e:
        logger.critical(f"Telemetry worker daemon crashed: {e}", exc_info=True)
