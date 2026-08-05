"""Register the backend's Zenoh handler declarations."""

from src.zenoh.generated import (
    LiveKitConsumeRequest,
    LiveKitUploadRequest,
    UserLoginRequest,
)
from src.zenoh.listeners import (
    LIVEKIT_CONSUME_KEY_EXPR,
    LIVEKIT_UPLOAD_KEY_EXPR,
    LOGIN_KEY_EXPR,
    livekit_consume,
    livekit_upload,
    user_login,
)
from src.zenoh.zenoh_handler import ZenohQueryHandler


def register_handlers(query_handler: ZenohQueryHandler) -> None:
    """Declare the request/reply handlers served by this backend."""
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
