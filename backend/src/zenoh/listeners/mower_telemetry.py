"""One-way Zenoh listener for mower telemetry batches."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.mower import add_telemetry_data_service
from src.zenoh.generated import TelemetryList
from src.zenoh.generated.paths import mower_telemetry_path

MOWER_TELEMETRY_KEY_EXPR = mower_telemetry_path("*")


async def mower_telemetry(
    payload: TelemetryList, db: AsyncSession
) -> None:
    """Buffer a telemetry batch; the sender does not receive a reply."""
    del db
    await add_telemetry_data_service(payload.root)
