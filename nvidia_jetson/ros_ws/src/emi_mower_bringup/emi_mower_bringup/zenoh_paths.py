"""Generated from backend/zenoh_asyncapi.yaml. Do not edit manually."""

USER_LOGIN_ADDRESS = "user/login"


def user_login_path() -> str:
    return USER_LOGIN_ADDRESS

ADD_MOWER_TO_USER_ADDRESS = "user/add_mower"


def add_mower_to_user_path() -> str:
    return ADD_MOWER_TO_USER_ADDRESS

UPDATE_USER_NAME_ADDRESS = "user/update_name"


def update_user_name_path() -> str:
    return UPDATE_USER_NAME_ADDRESS

UPDATE_MOWER_NAME_ADDRESS = "mower/{mower_id}/update_name"


def update_mower_name_path(mower_id: str) -> str:
    return (
        UPDATE_MOWER_NAME_ADDRESS
        .replace("{mower_id}", mower_id)
    )

UPDATE_USER_EMAIL_ADDRESS = "user/update_email"


def update_user_email_path() -> str:
    return UPDATE_USER_EMAIL_ADDRESS

LIVEKIT_CONSUME_ADDRESS = "mower/{mower_id}/livekit/consume"


def livekit_consume_path(mower_id: str) -> str:
    return (
        LIVEKIT_CONSUME_ADDRESS
        .replace("{mower_id}", mower_id)
    )

LIVEKIT_UPLOAD_ADDRESS = "mower/{mower_id}/livekit/upload"


def livekit_upload_path(mower_id: str) -> str:
    return (
        LIVEKIT_UPLOAD_ADDRESS
        .replace("{mower_id}", mower_id)
    )

MOWER_JOYSTICK_ADDRESS = "mower/{mower_id}/joystick"


def mower_joystick_path(mower_id: str) -> str:
    return (
        MOWER_JOYSTICK_ADDRESS
        .replace("{mower_id}", mower_id)
    )

MOWER_COMMAND_ADDRESS = "mower/{mower_id}/command"


def mower_command_path(mower_id: str) -> str:
    return (
        MOWER_COMMAND_ADDRESS
        .replace("{mower_id}", mower_id)
    )

MOWER_TELEMETRY_HISTORY_ADDRESS = "mower/{mower_id}/telemetry/{telemetry_type}/old"


def mower_telemetry_history_path(mower_id: str, telemetry_type: str) -> str:
    return (
        MOWER_TELEMETRY_HISTORY_ADDRESS
        .replace("{mower_id}", mower_id)
        .replace("{telemetry_type}", telemetry_type)
    )

MOWER_TELEMETRY_ADDRESS = "mower/{mower_id}/telemetry"


def mower_telemetry_path(mower_id: str) -> str:
    return (
        MOWER_TELEMETRY_ADDRESS
        .replace("{mower_id}", mower_id)
    )

CUTOUT_UPLOAD_URL_ADDRESS = "user/cutouts/upload-url"


def cutout_upload_url_path() -> str:
    return CUTOUT_UPLOAD_URL_ADDRESS

CUTOUT_UPLOADED_ADDRESS = "user/cutouts/uploaded"


def cutout_uploaded_path() -> str:
    return CUTOUT_UPLOADED_ADDRESS

MOWER_CUTOUT_DOWNLOAD_URL_ADDRESS = "mower/{mower_id}/cutout/download-url"


def mower_cutout_download_url_path(mower_id: str) -> str:
    return (
        MOWER_CUTOUT_DOWNLOAD_URL_ADDRESS
        .replace("{mower_id}", mower_id)
    )
