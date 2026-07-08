from src.config.socketio import logger, sio


@sio.event
async def disconnect(sid):
    """
    Fired when a Socket.IO client disconnects.
    """
    logger.info(f"Socket.IO client disconnected: {sid}")
