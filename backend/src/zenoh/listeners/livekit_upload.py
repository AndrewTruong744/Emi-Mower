"""LiveKit upload-token query listener."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.livekit import livekit_upload_service
from src.zenoh.generated import LiveKitTokenResponse, LiveKitUploadRequest
from src.zenoh.listeners.livekit import mower_id_from_query_key

LIVEKIT_UPLOAD_KEY_EXPR = "mower/*/livekit/upload"


async def livekit_upload(
    payload: LiveKitUploadRequest, db: AsyncSession, key_expr: str
) -> LiveKitTokenResponse:
    """Issue a publish-only token for the mower authorized by Zenoh ACLs."""
    del payload, db
    mower_id = mower_id_from_query_key(key_expr, "upload")
    return await livekit_upload_service(mower_id)
