"""Register the backend's Zenoh handler declarations."""

from src.schemas.valkey import TelemetryListCache
from src.zenoh.generated import (
    AddMowerToUserRequest,
    LiveKitConsumeRequest,
    LiveKitUploadRequest,
    UpdateMowerNameRequest,
    UpdateUserEmailRequest,
    UpdateUserNameRequest,
    UserLoginRequest,
)
from src.zenoh.listeners import (
    ADD_MOWER_TO_USER_KEY_EXPR,
    LIVEKIT_CONSUME_KEY_EXPR,
    LIVEKIT_UPLOAD_KEY_EXPR,
    LOGIN_KEY_EXPR,
    MOWER_TELEMETRY_KEY_EXPR,
    UPDATE_MOWER_NAME_KEY_EXPR,
    UPDATE_USER_EMAIL_KEY_EXPR,
    UPDATE_USER_NAME_KEY_EXPR,
    add_mower_to_user,
    livekit_consume,
    livekit_upload,
    mower_telemetry,
    update_mower_name,
    update_user_email,
    update_user_name,
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
        ADD_MOWER_TO_USER_KEY_EXPR,
        add_mower_to_user,
        request_model=AddMowerToUserRequest,
    )
    query_handler.declare(
        UPDATE_USER_NAME_KEY_EXPR,
        update_user_name,
        request_model=UpdateUserNameRequest,
    )
    query_handler.declare(
        UPDATE_MOWER_NAME_KEY_EXPR,
        update_mower_name,
        request_model=UpdateMowerNameRequest,
        include_query_key=True,
    )
    query_handler.declare(
        UPDATE_USER_EMAIL_KEY_EXPR,
        update_user_email,
        request_model=UpdateUserEmailRequest,
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
