"""One-way Zenoh listener for mower telemetry batches."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.valkey import TelemetryListCache
from src.services.mower import add_telemetry_data_service

MOWER_TELEMETRY_KEY_EXPR = "mower/*/telemetry"


async def mower_telemetry(
    payload: TelemetryListCache, db: AsyncSession
) -> None:
    """Buffer a telemetry batch; the sender does not receive a reply."""
    del db
    await add_telemetry_data_service(payload.root)
