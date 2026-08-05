"""Register the backend's Zenoh handler declarations."""

from src.schemas.valkey import TelemetryListCache
from src.zenoh.generated import (
    LiveKitConsumeRequest,
    LiveKitUploadRequest,
    UserLoginRequest,
)
from src.zenoh.listeners import (
    LIVEKIT_CONSUME_KEY_EXPR,
    LIVEKIT_UPLOAD_KEY_EXPR,
    LOGIN_KEY_EXPR,
    MOWER_TELEMETRY_KEY_EXPR,
    livekit_consume,
    livekit_upload,
    mower_telemetry,
    user_login,
)
from src.zenoh.zenoh_handler import ZenohMessageHandler, ZenohQueryHandler


def register_handlers(
    query_handler: ZenohQueryHandler, message_handler: ZenohMessageHandler
) -> None:
    """Declare the request/reply and one-way handlers served by the backend."""
    query_handler.declare(
        LOGIN_KEY_EXPR,
        user_login,
        request_model=UserLoginRequest,
    )
    query_handler.declare(
        LIVEKIT_CONSUME_KEY_EXPR,
        livekit_consume,
        request_model=LiveKitConsumeRequest,
        include_query_key=True,
    )
    query_handler.declare(
        LIVEKIT_UPLOAD_KEY_EXPR,
        livekit_upload,
        request_model=LiveKitUploadRequest,
        include_query_key=True,
    )
    message_handler.declare(
        MOWER_TELEMETRY_KEY_EXPR,
        mower_telemetry,
        message_model=TelemetryListCache,
    )
