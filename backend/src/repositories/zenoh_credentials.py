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
    """Return users whose expiry is due or invalid and must be revoked."""
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
                "Invalid Zenoh credential expiry for user %s; revoking credential",
                user_id,
            )
            expired_user_ids.append(user_id)

    return expired_user_ids

async def remove_zenoh_credential_expiries(user_ids: list[str]) -> None:
    """Remove expiry records for router credentials deleted in the same batch."""
    if not user_ids:
        return

    try:
        async with get_valkey_client() as client:
            await client.hdel(ZENOH_TOKEN_EXPIRY_KEY, *user_ids)
    except Exception as err:
        logger.error("Failed to remove Zenoh credential expiries for %s", user_ids)
        raise RepositoryError(
            "Failed to remove Zenoh credential expiries"
        ) from err
