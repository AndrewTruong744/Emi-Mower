import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from src.exceptions import AuthenticationError

security_scheme = HTTPBearer(auto_error=True)
logger = logging.getLogger("services.auth")


async def verify_gcp_identity(
    cred: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI dependency that extracts the Bearer token, validates it against
    GCP Identity Platform, and returns the decoded user profile claims.
    Raises AuthenticationError on failure.
    """
    token = cred.credentials
    try:
        decoded_token = auth.verify_id_token(token, clock_skew_seconds=10)
        return decoded_token
    except Exception as err:
        logger.error(f"Token verification failed: {err}", exc_info=True)
        raise AuthenticationError(
            "Invalid, expired, or tampered authentication credentials"
        ) from err
