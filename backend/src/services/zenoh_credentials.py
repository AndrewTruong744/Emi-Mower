"""Coordinate the lifecycle of short-lived Zenoh user credentials."""

import logging
import time

from src.config import ZenohAdminClient
from src.repositories.zenoh_credentials import (
    get_expired_zenoh_credential_user_ids,
    record_zenoh_credential_expiry,
    remove_zenoh_credential_expiries,
)

logger = logging.getLogger("services.zenoh_credentials")


async def provision_zenoh_credential(
    user_id: str,
    mower_ids: list[str],
    password: str,
    ttl_seconds: int,
) -> None:
    """Configure a runtime credential and persist its expiry for cleanup."""
    await ZenohAdminClient().configure_user_app(
        user_id=user_id,
        mower_ids=mower_ids,
        password=password,
    )
    expires_at = int(time.time()) + ttl_seconds
    await record_zenoh_credential_expiry(user_id, expires_at)


async def remove_expired_zenoh_credentials(now: int) -> None:
    """Delete due router credentials, retaining failed entries for a retry."""
    client = ZenohAdminClient()
    expired_user_ids = await get_expired_zenoh_credential_user_ids(now)
    deleted_user_ids = []

    for user_id in expired_user_ids:
        try:
            await client.delete_user_password(user_id)
            deleted_user_ids.append(user_id)
        except Exception:
            logger.exception("Failed to remove expired credential for user %s", user_id)

    if not deleted_user_ids:
        return

    try:
        await remove_zenoh_credential_expiries(deleted_user_ids)
        logger.info(
            "Removed expiry records for %d Zenoh credentials", len(deleted_user_ids)
        )
    except Exception:
        logger.exception("Failed to remove expired Zenoh credential records")
