import logging

from src.config.mqtt import fast_mqtt
from src.config.socketio import sio
from src.config.valkey_client import get_valkey_client
from src.repositories.find_user_by_mower import find_user_by_mower

logger = logging.getLogger("mqtt.handle_mower_status")


@fast_mqtt.subscribe("/mower/+/status")
async def handle_mower_status_callback(client, topic: str, payload: bytes, qos: int, properties) -> None:
    """
    MQTT callback for mower online/offline status updates.
    1. Extracts mower_id from topic.
    2. Parses status string ('online' or 'offline').
    3. Looks up owner_id via find_user_by_mower.
    4. Updates Valkey status cache ('mower:{mower_id}:status').
    5. Emits Socket.IO 'mower.status' event to the owner.
    """
    logger.info(f"Received status update on topic: {topic}")

    # Parse mower_id from topic: /mower/{mower_id}/status
    parts = topic.strip("/").split("/")
    if len(parts) < 2:
        logger.error(f"Failed to parse mower ID from topic: {topic}")
        return
    mower_id = parts[1]

    # Decode and clean status string
    try:
        status_str = payload.decode("utf-8").strip().lower()
    except Exception as decode_err:
        logger.error(f"Failed to decode status payload: {decode_err}")
        return

    if status_str not in ("online", "offline"):
        logger.warning(
            f"Received unexpected status value '{status_str}' for mower {mower_id}"
        )
        return

    # Find mower owner
    owner_id = await find_user_by_mower(mower_id)
    if owner_id in ("dne", "fail"):
        logger.warning(
            "Could not resolve owner for mower %s (lookup: '%s')",
            mower_id,
            owner_id,
        )
        # We still update status in Valkey even if owner is not found
    else:
        logger.info(
            "Resolved owner %s for mower %s. Emitting status '%s'...",
            owner_id,
            mower_id,
            status_str,
        )
        # Broadcast Socket.IO update to the owner's room
        try:
            await sio.emit(
                "mower.status",
                {"mower_id": mower_id, "status": status_str},
                to=owner_id,
            )
            logger.info(
                f"Successfully emitted mower.status event to user {owner_id}"
            )
        except Exception as sio_err:
            logger.error(f"Failed to emit Socket.IO status event: {sio_err}")

    # Update status key in Valkey
    v_client = get_valkey_client()
    try:
        status_key = f"mower:{mower_id}:status"
        if status_str == "online":
            await v_client.set(status_key, "online")
            logger.info(f"Set Valkey key '{status_key}' to 'online'")
        else:
            await v_client.delete(status_key)
            logger.info(f"Deleted Valkey key '{status_key}'")
    except Exception as valkey_err:
        logger.error(
            f"Failed to update status in Valkey for mower {mower_id}: {valkey_err}"
        )
    finally:
        await v_client.close()
