"""LiveKit upload-token query listener."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.livekit import livekit_upload_service
from src.services.mower import mower_route_params
from src.zenoh.generated import LiveKitTokenResponse, LiveKitUploadRequest
from src.zenoh.generated.paths import livekit_upload_path

LIVEKIT_UPLOAD_KEY_EXPR = livekit_upload_path("*")


async def livekit_upload(
    payload: LiveKitUploadRequest, db: AsyncSession, key_expr: str
) -> LiveKitTokenResponse:
    """Issue a publish-only token for the mower authorized by Zenoh ACLs."""
    del payload, db
    (mower_id,) = mower_route_params(key_expr, LIVEKIT_UPLOAD_KEY_EXPR)
    result = await livekit_upload_service(mower_id)
    return LiveKitTokenResponse(**result)
