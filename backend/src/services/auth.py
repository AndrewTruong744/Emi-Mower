import logging

from firebase_admin import auth

from src.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger("services.auth")

async def verify_firebase_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return claims with a canonical user ID."""
    if not id_token:
        raise ValidationError("The request must contain a non-empty id_token")

    try:
        decoded_identity = auth.verify_id_token(id_token, clock_skew_seconds=10)
    except Exception as err:
        logger.error(f"Token verification failed: {err}", exc_info=True)
        raise AuthenticationError(
            "Invalid, expired, or tampered authentication credentials"
        ) from err

    user_id = decoded_identity.get("uid") or decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")
    return {**decoded_identity, "user_id": user_id}
