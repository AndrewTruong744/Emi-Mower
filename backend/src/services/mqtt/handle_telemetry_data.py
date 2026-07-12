import json
import logging
from datetime import datetime, timezone

from src.config.mqtt import register_mqtt_callback
from src.config.valkey_client import get_valkey_client

logger = logging.getLogger("mqtt.handle_telemetry_data")


async def handle_telemetry_data_callback(topic: str, payload: bytes) -> None:
    """
    MQTT callback for receiving telemetry data from the mower.
    Parses the JSON payload (expecting a single outer key with a nested object),
    injects/ensures uuid and timestamp, and pushes to a Valkey list under
    'mower:{uuid}:telemetry:data'.
    """
    logger.info(f"Received telemetry data on topic: {topic}")

    # Extract mower_uuid from topic /mower/{uuid}/telemetry/data
    parts = topic.strip("/").split("/")
    if len(parts) < 2:
        logger.error(f"Failed to parse mower UUID from topic: {topic}")
        return
    mower_uuid = parts[1]

    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {e}")
        return

    if not isinstance(data, dict) or not data:
        logger.error(f"Invalid telemetry payload structure: {data}")
        return

    # Extract the nested object from the single-key dictionary
    # E.g. {"telemetry": { ... }} or {"data": { ... }}
    outer_keys = list(data.keys())
    if len(outer_keys) != 1:
        logger.error(
            f"Expected exactly 1 outer key in telemetry payload, got keys: {outer_keys}"
        )
        return

    nested_obj = data[outer_keys[0]]
    if not isinstance(nested_obj, dict):
        logger.error(
            f"Expected nested telemetry data to be an object, got: {type(nested_obj)}"
        )
        return

    # Add/Ensure mower_uuid and timestamp in the nested telemetry object
    nested_obj["mower_id"] = mower_uuid
    if "timestamp" not in nested_obj:
        nested_obj["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Store into Valkey list mower:{uuid}:telemetry:data
    v_client = get_valkey_client()
    try:
        valkey_key = f"mower:{mower_uuid}:telemetry:data"
        valkey_value = json.dumps(nested_obj)
        logger.info(f"RPUSH to Valkey key '{valkey_key}'...")
        await v_client.rpush(valkey_key, valkey_value)
    except Exception as e:
        logger.error(f"Failed to store telemetry data in Valkey: {e}")
    finally:
        await v_client.close()


# Register the callback automatically on import
register_mqtt_callback(
    "/mower/+/telemetry/data", handle_telemetry_data_callback
)
