"""Register the backend's Zenoh handler declarations."""

from src.zenoh.generated import (
    AddMowerToUserRequest,
    CutoutUploadNotification,
    CutoutUploadUrlRequest,
    LiveKitConsumeRequest,
    LiveKitUploadRequest,
    TelemetryHistoryRequest,
    TelemetryList,
    MowerCutoutDownloadUrlRequest,
    UpdateMowerNameRequest,
    UpdateUserEmailRequest,
    UpdateUserNameRequest,
    UserLoginRequest,
)
from src.zenoh.listeners import (
    ADD_MOWER_TO_USER_KEY_EXPR,
    CUTOUT_UPLOADED_KEY_EXPR,
    CUTOUT_UPLOAD_URL_KEY_EXPR,
    LIVEKIT_CONSUME_KEY_EXPR,
    LIVEKIT_UPLOAD_KEY_EXPR,
    LOGIN_KEY_EXPR,
    MOWER_TELEMETRY_HISTORY_KEY_EXPR,
    MOWER_TELEMETRY_KEY_EXPR,
    MOWER_CUTOUT_DOWNLOAD_URL_KEY_EXPR,
    UPDATE_MOWER_NAME_KEY_EXPR,
    UPDATE_USER_EMAIL_KEY_EXPR,
    UPDATE_USER_NAME_KEY_EXPR,
    add_mower_to_user,
    cutout_uploaded,
    cutout_upload_url,
    livekit_consume,
    livekit_upload,
    mower_telemetry,
    mower_cutout_download_url,
    mower_telemetry_history,
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
        MOWER_TELEMETRY_HISTORY_KEY_EXPR,
        mower_telemetry_history,
        request_model=TelemetryHistoryRequest,
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
    query_handler.declare(
        CUTOUT_UPLOAD_URL_KEY_EXPR,
        cutout_upload_url,
        request_model=CutoutUploadUrlRequest,
    )
    query_handler.declare(
        MOWER_CUTOUT_DOWNLOAD_URL_KEY_EXPR,
        mower_cutout_download_url,
        request_model=MowerCutoutDownloadUrlRequest,
        include_query_key=True,
    )
    message_handler.declare(
        MOWER_TELEMETRY_KEY_EXPR,
        mower_telemetry,
        message_model=TelemetryList,
    )
    message_handler.declare(
        CUTOUT_UPLOADED_KEY_EXPR,
        cutout_uploaded,
        message_model=CutoutUploadNotification,
    )
