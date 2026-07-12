import json
import logging

from src.config.mqtt import publish_message
from src.config.socketio import sio
from src.repositories.verify_ownership import verify_ownership

logger = logging.getLogger("socketio.mower_telemetry")


@sio.on("mower.telemetry")
async def handle_mower_telemetry(sid, data):
    """
    Socket.IO handler for receiving mower telemetry commands from the app
    and forwarding them to MQTT.
    """
    logger.info(f"Received mower.telemetry event from sid {sid} with data: {data}")

    if not isinstance(data, dict):
        logger.warning(f"Invalid telemetry data type received: {type(data)}")
        await sio.emit("mower.telemetry", {"error": "Invalid data format"}, to=sid)
        return

    mower_id = data.get("mower_id")
    if not mower_id:
        logger.warning(f"mower_id missing in telemetry data from sid {sid}")
        await sio.emit("mower.telemetry", {"error": "mower_id is required"}, to=sid)
        return

    # Get user_id from socket session
    async with sio.session(sid) as session:
        user_id = session.get("user_id")

    if not user_id:
        logger.warning(f"Unauthenticated session {sid} attempted to send telemetry.")
        await sio.emit("mower.telemetry", {"error": "Authentication required"}, to=sid)
        return

    # Verify ownership
    is_owner = await verify_ownership(user_id, mower_id)
    if not is_owner:
        logger.warning(f"User {user_id} does not own mower {mower_id}")
        await sio.emit("mower.telemetry", {"error": "Permission denied"}, to=sid)
        return

    # Send to MQTT topic /mower/{uuid}/telemetry/command for movement
    topic = f"/mower/{mower_id}/telemetry/command"
    try:
        # Ensure that the MQTT is in QoS 0 to prevent stale commands
        payload = json.dumps(data)
        await publish_message(topic, payload, qos=0)
        logger.info(f"Successfully published telemetry command to MQTT topic {topic}")
    except Exception as e:
        logger.error(f"Failed to publish telemetry to MQTT: {e}")
        await sio.emit(
            "mower.telemetry",
            {"error": "Failed to send command to mower"},
            to=sid,
        )


