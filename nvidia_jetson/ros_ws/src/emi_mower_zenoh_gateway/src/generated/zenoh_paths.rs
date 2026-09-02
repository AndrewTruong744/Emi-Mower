//! Generated from `backend/zenoh_asyncapi.yaml`. Do not edit manually.
//!
//! Regenerate with `backend/scripts/generate_types.sh`.

pub const USER_LOGIN_ADDRESS: &str = "user/login";

pub fn user_login_path() -> String {
    let path = USER_LOGIN_ADDRESS.to_owned();

    path
}

pub const ADD_MOWER_TO_USER_ADDRESS: &str = "user/add_mower";

pub fn add_mower_to_user_path() -> String {
    let path = ADD_MOWER_TO_USER_ADDRESS.to_owned();

    path
}

pub const UPDATE_USER_NAME_ADDRESS: &str = "user/update_name";

pub fn update_user_name_path() -> String {
    let path = UPDATE_USER_NAME_ADDRESS.to_owned();

    path
}

pub const UPDATE_MOWER_NAME_ADDRESS: &str = "mower/{mower_id}/update_name";

pub fn update_mower_name_path(mower_id: &str) -> String {
    let mut path = UPDATE_MOWER_NAME_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}

pub const UPDATE_USER_EMAIL_ADDRESS: &str = "user/update_email";

pub fn update_user_email_path() -> String {
    let path = UPDATE_USER_EMAIL_ADDRESS.to_owned();

    path
}

pub const LIVEKIT_CONSUME_ADDRESS: &str = "mower/{mower_id}/livekit/consume";

pub fn livekit_consume_path(mower_id: &str) -> String {
    let mut path = LIVEKIT_CONSUME_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}

pub const LIVEKIT_UPLOAD_ADDRESS: &str = "mower/{mower_id}/livekit/upload";

pub fn livekit_upload_path(mower_id: &str) -> String {
    let mut path = LIVEKIT_UPLOAD_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}

pub const MOWER_JOYSTICK_ADDRESS: &str = "mower/{mower_id}/joystick";

pub fn mower_joystick_path(mower_id: &str) -> String {
    let mut path = MOWER_JOYSTICK_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}

pub const MOWER_COMMAND_ADDRESS: &str = "mower/{mower_id}/command";

pub fn mower_command_path(mower_id: &str) -> String {
    let mut path = MOWER_COMMAND_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}

pub const MOWER_TELEMETRY_HISTORY_ADDRESS: &str = "mower/{mower_id}/telemetry/{telemetry_type}/old";

pub fn mower_telemetry_history_path(mower_id: &str, telemetry_type: &str) -> String {
    let mut path = MOWER_TELEMETRY_HISTORY_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path = path.replace("{telemetry_type}", telemetry_type);
    path
}

pub const MOWER_TELEMETRY_ADDRESS: &str = "mower/{mower_id}/telemetry";

pub fn mower_telemetry_path(mower_id: &str) -> String {
    let mut path = MOWER_TELEMETRY_ADDRESS.to_owned();
    path = path.replace("{mower_id}", mower_id);
    path
}
