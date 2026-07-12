import logging

import socketio

# Configure logging for Socket.IO
logger = logging.getLogger("socketio")
logger.setLevel(logging.INFO)

# Initialize Socket.IO AsyncServer
# Disable noisy library logs by default; set True for debugging
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

# Wrap the Socket.IO server as an ASGI application
# The default socketio_path is "socket.io".
# If mounted at "/ws" in FastAPI, the client connection path will be "/ws/socket.io".
sio_app = socketio.ASGIApp(socketio_server=sio, socketio_path="socket.io")

# Import event handlers to register them on the sio instance
# ruff: noqa: E402
import src.services.sockets.connect  # noqa: F401
import src.services.sockets.consume_video  # noqa: F401
import src.services.sockets.disconnect  # noqa: F401
import src.services.sockets.mower_command  # noqa: F401
import src.services.sockets.mower_telemetry  # noqa: F401
import src.services.sockets.ping  # noqa: F401

