"""LiveKit consume-token query listener."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.livekit import livekit_consume_service
from src.zenoh.generated import LiveKitConsumeRequest, LiveKitTokenResponse
from src.zenoh.generated.paths import livekit_consume_path
from src.zenoh.listeners.livekit import mower_id_from_query_key

LIVEKIT_CONSUME_KEY_EXPR = livekit_consume_path("*")


async def livekit_consume(
    payload: LiveKitConsumeRequest, db: AsyncSession, key_expr: str
) -> LiveKitTokenResponse:
    """Issue a subscribe-only token for the mower authorized by Zenoh ACLs."""
    del payload, db
    mower_id = mower_id_from_query_key(key_expr, "consume")
    return await livekit_consume_service(mower_id)
