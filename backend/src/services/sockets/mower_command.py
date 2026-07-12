import logging

from src.config.mqtt import publish_message
from src.config.socketio import sio
from src.repositories.verify_ownership import verify_ownership

logger = logging.getLogger("socketio.mower_command")


@sio.on("mower.command")
async def handle_mower_command(sid, data):
    """
    Socket.IO handler for receiving mower state commands from the app
    and forwarding them to MQTT.
    """
    logger.info(f"Received mower.command event from sid {sid} with data: {data}")

    if not isinstance(data, dict):
        logger.warning(f"Invalid command data type received: {type(data)}")
        await sio.emit("mower.command", {"error": "Invalid data format"}, to=sid)
        return

    mower_id = data.get("mower_id")
    command = data.get("command")

    if not mower_id or not command:
        logger.warning(f"mower_id or command missing in data from sid {sid}")
        await sio.emit(
            "mower.command",
            {"error": "mower_id and command are required"},
            to=sid,
        )
        return

    valid_commands = {
        "disable",
        "active",
        "power_off",
        "power_on",
        "stream_stop",
        "stream_start",
        "auto_on",
        "auto_off",
    }
    if command not in valid_commands:
        logger.warning(f"Invalid command '{command}' from sid {sid}")
        await sio.emit(
            "mower.command",
            {
                "error": f"Invalid command. Must be one of {list(valid_commands)}"
            },
            to=sid,
        )
        return

    # Get user_id from socket session
    async with sio.session(sid) as session:
        user_id = session.get("user_id")

    if not user_id:
        logger.warning(f"Unauthenticated session {sid} attempted to send command.")
        await sio.emit("mower.command", {"error": "Authentication required"}, to=sid)
        return

    # Verify ownership
    is_owner = await verify_ownership(user_id, mower_id)
    if not is_owner:
        logger.warning(f"User {user_id} does not own mower {mower_id}")
        await sio.emit("mower.command", {"error": "Permission denied"}, to=sid)
        return

    # Send to MQTT topic /mower/{uuid}/command
    topic = f"/mower/{mower_id}/command"
    try:
        await publish_message(topic, command, qos=0)
        logger.info(
            f"Successfully published command '{command}' to MQTT topic {topic}"
        )
    except Exception as e:
        logger.error(f"Failed to publish command to MQTT: {e}")
        await sio.emit(
            "mower.command",
            {"error": "Failed to send command to mower"},
            to=sid,
        )
