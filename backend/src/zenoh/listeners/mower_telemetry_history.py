"""Zenoh query listener for paged historical mower graph telemetry."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationError
from src.services.auth import verify_zenoh_google_id_token
from src.services.mower import get_telemetry_history_service
from src.zenoh.generated import TelemetryHistoryRequest, TelemetryHistoryResponse

MOWER_TELEMETRY_HISTORY_KEY_EXPR = "mower/*/telemetry/*/old"


def _telemetry_path_from_query_key(key_expr: str) -> tuple[str, str]:
    """Extract mower ID and metric from mower/{id}/telemetry/{type}/old."""
    parts = str(key_expr).split("/")
    if (
        len(parts) != 5
        or parts[0] != "mower"
        or not parts[1]
        or parts[2] != "telemetry"
        or not parts[3]
        or parts[4] != "old"
    ):
        raise ValidationError("Invalid mower telemetry history query path")
    return parts[1], parts[3]


async def mower_telemetry_history(
    payload: TelemetryHistoryRequest, db: AsyncSession, key_expr: str
) -> TelemetryHistoryResponse:
    """Verify Firebase identity and ownership before exposing graph history."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")
    mower_id, telemetry_type = _telemetry_path_from_query_key(key_expr)
    return await get_telemetry_history_service(
        user_id, mower_id, telemetry_type, payload.cursor, db
    )
