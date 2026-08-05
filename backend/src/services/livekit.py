"""LiveKit access-token services."""

from datetime import timedelta
from uuid import uuid4

from livekit import api

from src.config.settings import settings
from src.exceptions import TokenGenerationError, ValidationError
from src.zenoh.generated import LiveKitTokenResponse

LIVEKIT_TOKEN_TTL_SECONDS = 60 * 60


def _livekit_token(
    *, identity: str, room: str, can_publish: bool, can_subscribe: bool
) -> str:
    """Create a narrowly scoped LiveKit room token."""
    try:
        return (
            api.AccessToken(
                api_key=settings.LIVEKIT_API_KEY,
                api_secret=settings.LIVEKIT_API_SECRET,
            )
            .with_ttl(timedelta(seconds=LIVEKIT_TOKEN_TTL_SECONDS))
            .with_identity(identity)
            .with_grants(
                api.VideoGrants(
                    room=room,
                    room_join=True,
                    can_publish=can_publish,
                    can_subscribe=can_subscribe,
                )
            )
            .to_jwt()
        )
    except Exception as error:
        raise TokenGenerationError("Failed to generate LiveKit access token") from error


def _token_response(token: str) -> LiveKitTokenResponse:
    return LiveKitTokenResponse(
        token=token,
        url=settings.LIVEKIT_URL,
        expires_in=LIVEKIT_TOKEN_TTL_SECONDS,
    )


async def livekit_consume_service(mower_id: str) -> LiveKitTokenResponse:
    """Issue a subscribe-only token for the mower room authorized by Zenoh."""
    if not mower_id:
        raise ValidationError("mower_id is required")

    token = _livekit_token(
        identity=f"consumer-{uuid4()}",
        room=mower_id,
        can_publish=False,
        can_subscribe=True,
    )
    return _token_response(token)


async def livekit_upload_service(mower_id: str) -> LiveKitTokenResponse:
    """Issue a publish-only token to a mower for its own room."""
    if not mower_id:
        raise ValidationError("mower_id is required")

    token = _livekit_token(
        identity=mower_id,
        room=mower_id,
        can_publish=True,
        can_subscribe=False,
    )
    return _token_response(token)


# Explicit aliases keep the service naming convenient for callers that use the
# action-first convention used by the Zenoh listener modules.
get_livekit_consume_token_service = livekit_consume_service
get_livekit_upload_token_service = livekit_upload_service
