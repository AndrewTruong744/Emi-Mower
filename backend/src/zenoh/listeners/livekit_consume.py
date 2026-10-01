"""LiveKit consume-token query listener."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.livekit import livekit_consume_service
from src.services.mower import mower_route_params
from src.zenoh.generated import LiveKitConsumeRequest, LiveKitTokenResponse
from src.zenoh.generated.paths import livekit_consume_path

LIVEKIT_CONSUME_KEY_EXPR = livekit_consume_path("*")


async def livekit_consume(
    payload: LiveKitConsumeRequest, db: AsyncSession, key_expr: str
) -> LiveKitTokenResponse:
    """Issue a subscribe-only token for the mower authorized by Zenoh ACLs."""
    del payload, db
    (mower_id,) = mower_route_params(key_expr, LIVEKIT_CONSUME_KEY_EXPR)
    result = await livekit_consume_service(mower_id)
    return LiveKitTokenResponse(**result)
