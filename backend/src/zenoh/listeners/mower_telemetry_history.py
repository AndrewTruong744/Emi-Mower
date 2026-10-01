"""Zenoh query listener for paged historical mower graph telemetry."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_firebase_id_token
from src.services.mower import get_telemetry_history_service, mower_route_params
from src.zenoh.generated import (
    TelemetryHistoryPoint,
    TelemetryHistoryRequest,
    TelemetryHistoryResponse,
)
from src.zenoh.generated.paths import mower_telemetry_history_path

MOWER_TELEMETRY_HISTORY_KEY_EXPR = mower_telemetry_history_path("*", "*")


async def mower_telemetry_history(
    payload: TelemetryHistoryRequest, db: AsyncSession, key_expr: str
) -> TelemetryHistoryResponse:
    """Verify Firebase identity and ownership before exposing graph history."""
    identity = await verify_firebase_id_token(payload.id_token)
    user_id = identity["user_id"]
    mower_id, telemetry_type = mower_route_params(
        key_expr, MOWER_TELEMETRY_HISTORY_KEY_EXPR
    )
    result = await get_telemetry_history_service(
        user_id, mower_id, telemetry_type, payload.cursor, db
    )
    return TelemetryHistoryResponse(
        telemetry_type=result["telemetry_type"],
        limit=result["limit"],
        total=result["total"],
        has_more=result["next_cursor"] is not None,
        next_cursor=result["next_cursor"],
        points=[
            TelemetryHistoryPoint(
                timestamp=timestamp.isoformat()
                if isinstance(timestamp, datetime)
                else timestamp,
                value=value,
            )
            for timestamp, value in result["points"]
        ],
    )
