import logging

from firebase_admin import auth

from src.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger("services.auth")


async def _verify_google_id_token(token: str) -> dict:
    """Verify a raw Google/Firebase ID token and return its decoded claims."""
    try:
        return auth.verify_id_token(token, clock_skew_seconds=10)
    except Exception as err:
        logger.error(f"Token verification failed: {err}", exc_info=True)
        raise AuthenticationError(
            "Invalid, expired, or tampered authentication credentials"
        ) from err
    
async def verify_zenoh_google_id_token(id_token: str) -> dict:
    """Verify a Zenoh Google/Firebase ID token and require a user ID claim."""
    if not id_token:
        raise ValidationError("The request must contain a non-empty id_token")

    decoded_identity = await _verify_google_id_token(id_token)
    user_id = decoded_identity.get("uid") or decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")
    return decoded_identity
