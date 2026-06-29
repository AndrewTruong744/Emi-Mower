import logging
import socketio

# Configure logging for Socket.IO
logger = logging.getLogger("socketio")
logger.setLevel(logging.INFO)

# Initialize Socket.IO AsyncServer
# cors_allowed_origins="*" allows all origins for simplicity in local development,
# but can be restricted to specific domains in production settings.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,  # Disable noisy internal library logs by default, set True for debugging
    engineio_logger=False,  # Disable noisy low-level connection logs by default, set True for debugging
)

# Wrap the Socket.IO server as an ASGI application
# The default socketio_path is "socket.io".
# If mounted at "/ws" in FastAPI, the client connection path will be "/ws/socket.io".
sio_app = socketio.ASGIApp(socketio_server=sio, socketio_path="socket.io")

# Standard Event Handlers (move to sockets folder)


@sio.event
async def connect(sid, environ, auth=None):
    """
    Fired when a Socket.IO client establishes a connection.
    The 'auth' parameter can be used to pass JWT/Firebase tokens from the client.
    """
    logger.info(f"Socket.IO client connected: {sid} (auth={auth})")
    await sio.emit(
        "welcome",
        {"message": "Connected to Emi Mower Real-time Server!", "sid": sid},
        to=sid,
    )


@sio.event
async def disconnect(sid):
    """
    Fired when a Socket.IO client disconnects.
    """
    logger.info(f"Socket.IO client disconnected: {sid}")


# Example event handler for ping-pong testing
@sio.on("ping")
async def handle_ping(sid, data=None):
    """
    A simple ping event to test roundtrip communication.
    """
    logger.info(f"Received ping from {sid} with data: {data}")
    await sio.emit("pong", {"message": "pong", "received_data": data}, to=sid)
