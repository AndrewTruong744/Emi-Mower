"""Valkey persistence for short-lived Zenoh user credentials."""

import logging

from src.config.valkey_client import get_valkey_client
from src.exceptions import RepositoryError
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

logger = logging.getLogger("repositories.zenoh_credentials")


async def record_zenoh_credential_expiry(user_id: str, expires_at: int) -> None:
    """Record when the router credential provisioned for a user expires."""
    try:
        async with get_valkey_client() as client:
            await client.hset(
                ZENOH_TOKEN_EXPIRY_KEY,
                mapping={user_id: str(expires_at)},
            )
    except Exception as err:
        logger.error("Failed to record Zenoh credential expiry for %s", user_id)
        raise RepositoryError(
            f"Failed to record Zenoh credential expiry for user '{user_id}'"
        ) from err


async def get_expired_zenoh_credential_user_ids(now: int) -> list[str]:
    """Return users whose recorded Zenoh credential expiration is due."""
    try:
        async with get_valkey_client() as client:
            expiry_map = await client.hgetall(ZENOH_TOKEN_EXPIRY_KEY)
    except Exception as err:
        logger.error("Failed to read Zenoh credential expirations")
        raise RepositoryError("Failed to read Zenoh credential expirations") from err

    expired_user_ids = []
    for user_id, expires_at in expiry_map.items():
        try:
            if int(expires_at) <= now:
                expired_user_ids.append(user_id)
        except (TypeError, ValueError):
            logger.warning(
                "Ignoring invalid Zenoh credential expiry for user %s", user_id
            )

    return expired_user_ids


async def remove_zenoh_credential_expiry(user_id: str) -> None:
    """Remove the expiration record once the router credential is deleted."""
    try:
        async with get_valkey_client() as client:
            await client.hdel(ZENOH_TOKEN_EXPIRY_KEY, user_id)
    except Exception as err:
        logger.error("Failed to remove Zenoh credential expiry for %s", user_id)
        raise RepositoryError(
            f"Failed to remove Zenoh credential expiry for user '{user_id}'"
        ) from err
