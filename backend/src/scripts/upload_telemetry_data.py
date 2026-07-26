import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone

from src.config.database import AsyncSessionLocal
from src.config.valkey_client import get_valkey_client
from src.models.mower import MowerImuModel, MowerTelemetryModel

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
            data_dict = json.loads(item)
        except Exception as e:
            logger.error(f"Failed to parse JSON item from list: {e}. Skipping.")
            continue

        mower_id_str = data_dict.get("mower_id")
        if not mower_id_str:
            logger.error("Missing mower_id in telemetry item. Skipping.")
            continue

        try:
            mower_id = uuid.UUID(mower_id_str)
        except ValueError as e:
            logger.error(f"Invalid mower_uuid format '{mower_id_str}': {e}. Skipping.")
            continue

        # Parse timestamp (expecting ISO format)
        timestamp_val = data_dict.get("timestamp")
        if isinstance(timestamp_val, str):
            try:
                # fromisoformat handles standard UTC Z/offsets in python 3.11+
                timestamp = datetime.fromisoformat(timestamp_val.replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(
                    "Failed to parse timestamp '%s': %s. Using current UTC.",
                    timestamp_val,
                    e,
                )
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        telemetry_entry = MowerTelemetryModel(
            mower_id=mower_id,
            timestamp=timestamp,
            latitude=float(data_dict.get("latitude", 0.0)),
            longitude=float(data_dict.get("longitude", 0.0)),
            battery_percentage=int(data_dict.get("battery_percentage", 0)),
            left_motor_speed=float(data_dict.get("left_motor_speed", 0.0)),
            left_motor_direction=int(data_dict.get("left_motor_direction", 0)),
            right_motor_speed=float(data_dict.get("right_motor_speed", 0.0)),
            right_motor_direction=int(data_dict.get("right_motor_direction", 0)),
            cutting_motor_speed=float(data_dict.get("cutting_motor_speed", 0.0)),
            slippage_detected=bool(data_dict.get("slippage_detected", False)),
            rgb_image_url=data_dict.get("rgb_image_url"),
            lidar_image_url=data_dict.get("lidar_image_url"),
        )

        # Parse nested IMU data if exists
        imu_dict = data_dict.get("imu_data")
        if imu_dict and isinstance(imu_dict, dict):
            imu_entry = MowerImuModel(
                accel_x=float(imu_dict.get("accel_x", 0.0)),
                accel_y=float(imu_dict.get("accel_y", 0.0)),
                accel_z=float(imu_dict.get("accel_z", 0.0)),
                gyro_x=float(imu_dict.get("gyro_x", 0.0)),
                gyro_y=float(imu_dict.get("gyro_y", 0.0)),
                gyro_z=float(imu_dict.get("gyro_z", 0.0)),
                mag_x=float(imu_dict.get("mag_x", 0.0)),
                mag_y=float(imu_dict.get("mag_y", 0.0)),
                mag_z=float(imu_dict.get("mag_z", 0.0)),
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
        temp_keys = await v_client.keys("mower:*:telemetry:data:temp")
        if temp_keys:
            logger.info(f"Found {len(temp_keys)} leftover temp keys to process.")
            for temp_key in temp_keys:
                await process_key(v_client, temp_key)

        # 2. Scan for active telemetry lists
        active_keys = await v_client.keys("mower:*:telemetry:data")
        if not active_keys:
            logger.info("No new telemetry data found in Valkey.")
            return

        logger.info(f"Found {len(active_keys)} active telemetry lists in Valkey.")

        # 3. Rename active keys to temp keys and process them
        for key in active_keys:
            temp_key = f"{key}:temp"
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
