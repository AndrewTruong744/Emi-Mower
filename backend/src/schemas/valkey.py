"""Authoritative Valkey key definitions and value contracts.

Every application-owned Valkey key, pattern, TTL, and key-format helper belongs
here. Values are JSON strings unless their key documentation says otherwise.
Cache-aside entries use a common default lifetime; callers refresh that lifetime
when they read a cached value.
"""

from datetime import datetime

from pydantic import BaseModel, RootModel

# Cache entries are written with ``setex`` throughout the repositories.
VALKEY_CACHE_TTL_SECONDS = 86_400

# Cache-aside JSON values. Values in braces are identifiers supplied by callers.
USER_MOWERS_KEY = "user:{user_id}:mowers"
USER_DATA_KEY = "user:{user_id}:data"
MOWER_DATA_KEY = "mower:{mower_id}:data"

# A HASH mapping user ID fields to decimal Unix-expiry-time values. It is an
# expiry registry only; it never stores the router credentials themselves.
ZENOH_TOKEN_EXPIRY_KEY = "user:zenoh_tokens"

# The telemetry worker uses a Valkey LIST at this key and temporarily renames
# it to the same key with ``:temp`` appended while it uploads the records.
MOWER_TELEMETRY_KEY = "mower:{mower_id}:telemetry:data"
MOWER_TELEMETRY_TEMP_KEY = "mower:{mower_id}:telemetry:data:temp"
MOWER_TELEMETRY_PATTERN = "mower:*:telemetry:data"
MOWER_TELEMETRY_TEMP_PATTERN = "mower:*:telemetry:data:temp"

# A STRING whose value is the mower ID. The one-time nonce is in the key and
# expires after the renewal challenge lifetime.
MOWER_CERTIFICATE_RENEWAL_NONCE_KEY = "mower_certificate_renewal:{mower_id}:{nonce}"
MOWER_CERTIFICATE_RENEWAL_NONCE_TTL_SECONDS = 300


def user_mowers_key(user_id: str) -> str:
    """Return the key containing a user's JSON list of mower IDs."""

    return USER_MOWERS_KEY.format(user_id=user_id)


def user_data_key(user_id: str) -> str:
    """Return the key containing a user's JSON-serialized data."""

    return USER_DATA_KEY.format(user_id=user_id)


def mower_data_key(mower_id: str) -> str:
    """Return the key containing a mower's JSON-serialized data."""

    return MOWER_DATA_KEY.format(mower_id=mower_id)


def mower_telemetry_key(mower_id: str) -> str:
    """Return the telemetry LIST key used by the upload worker."""

    return MOWER_TELEMETRY_KEY.format(mower_id=mower_id)


def mower_telemetry_temp_key(mower_id: str) -> str:
    """Return the temporary telemetry LIST key used during upload."""

    return MOWER_TELEMETRY_TEMP_KEY.format(mower_id=mower_id)


def mower_id_from_telemetry_key(key: str) -> str:
    """Extract the mower ID from a canonical active telemetry LIST key."""

    prefix = MOWER_TELEMETRY_KEY.partition("{mower_id}")[0]
    suffix = MOWER_TELEMETRY_KEY.partition("{mower_id}")[2]
    if not key.startswith(prefix) or not key.endswith(suffix):
        raise ValueError(f"not a canonical telemetry key: {key!r}")
    mower_id = key.removeprefix(prefix).removesuffix(suffix)
    if not mower_id:
        raise ValueError(f"not a canonical telemetry key: {key!r}")
    return mower_id


def mower_certificate_renewal_nonce_key(mower_id: str, nonce: str) -> str:
    """Return the one-time certificate-renewal challenge key for a mower."""

    return MOWER_CERTIFICATE_RENEWAL_NONCE_KEY.format(mower_id=mower_id, nonce=nonce)


class UserMowersCache(RootModel[list[str]]):
    """JSON value for ``user:{user_id}:mowers``."""


class UserDataCache(BaseModel):
    """JSON value for ``user:{user_id}:data``."""

    id: str
    email: str
    name: str
    created_at: datetime | None = None


class MowerDataCache(BaseModel):
    """JSON value for ``mower:{mower_id}:data``, including its owner."""

    id: str
    nickname: str
    owner_id: str | None = None
