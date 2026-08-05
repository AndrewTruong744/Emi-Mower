"""Helpers shared by the LiveKit Zenoh query listeners."""

from src.exceptions import ValidationError


def mower_id_from_query_key(key_expr: str, action: str) -> str:
    """Extract and validate the mower ID from a LiveKit query key."""
    parts = str(key_expr).split("/")
    if (
        len(parts) != 4
        or parts[0] != "mower"
        or not parts[1]
        or parts[2] != "livekit"
        or parts[3] != action
    ):
        raise ValidationError(f"Invalid LiveKit {action} query path")
    return parts[1]
