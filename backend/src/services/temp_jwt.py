import logging
import time

import jwt

from src.config.settings import settings
from src.exceptions import TokenGenerationError

logger = logging.getLogger("services.temp_jwt")


def generate_jwt_token(user_id: str, exp_seconds: int = 3600) -> str:
    """
    Generates a JWT token for a given user_id signed with settings.JWT_SECRET.
    Returns the encoded JWT token string or raises TokenGenerationError.
    """
    try:
        now = int(time.time())
        payload = {
            "sub": user_id,
            "user_id": user_id,
            "iat": now,
            "exp": now + exp_seconds,
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token
    except Exception as err:
        logger.error(f"Failed to generate JWT token for user {user_id}: {err}", exc_info=True)
        raise TokenGenerationError(f"Failed to generate JWT token for user '{user_id}'") from err


# Alias for compatibility if imported as generate_jwt
generate_jwt = generate_jwt_token
