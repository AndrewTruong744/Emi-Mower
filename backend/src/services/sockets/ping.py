from src.config.socketio import logger, sio


# Example event handler for ping-pong testing
@sio.on("ping")
async def handle_ping(sid, data=None):
    """
    A simple ping event to test roundtrip communication.
    """
    logger.info(f"Received ping from {sid} with data: {data}")
    await sio.emit("pong", {"message": "pong", "received_data": data}, to=sid)
