//! Rust-side constants shared with the mower's Zenoh API.

use zenoh as _;

pub const ZENOH_VERSION: &str = "1.9.0";
pub const LIVEKIT_UPLOAD_KEY_PREFIX: &str = "mower/";

pub fn livekit_upload_key(mower_id: &str) -> String {
    assert!(!mower_id.is_empty(), "mower ID must not be empty");
    assert!(!mower_id.contains('/'), "mower ID must be one Zenoh path segment");
    format!("mower/{mower_id}/livekit/upload")
}
