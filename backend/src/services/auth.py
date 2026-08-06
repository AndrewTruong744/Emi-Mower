import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from src.exceptions import AuthenticationError, ValidationError

security_scheme = HTTPBearer(auto_error=True)
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


async def verify_http_google_id_token(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI dependency that extracts the Bearer token, validates it against
    GCP Identity Platform, and returns the decoded user profile claims.
    Raises AuthenticationError on failure.
    """
    return await _verify_google_id_token(cred.credentials)


async def verify_zenoh_google_id_token(id_token: str) -> dict:
    """Verify a Zenoh Google/Firebase ID token and require a user ID claim."""
    if not id_token:
        raise ValidationError("The request must contain a non-empty id_token")

    decoded_identity = await _verify_google_id_token(id_token)
    user_id = decoded_identity.get("uid") or decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")
    return decoded_identity
