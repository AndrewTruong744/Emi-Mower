"""Remove expired dynamically provisioned Zenoh user credentials."""

import asyncio
import logging
import time

from src.config import ZenohAdminClient
from src.config.http_client import close_http_client
from src.repositories.zenoh_credentials import (
    get_expired_zenoh_credential_user_ids,
    remove_zenoh_credential_expiry,
)

CHECK_INTERVAL_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.remove_usrpwds_from_zenoh")


async def remove_expired_usrpwds() -> None:
    client = ZenohAdminClient()
    now = int(time.time())

    expired_user_ids = await get_expired_zenoh_credential_user_ids(now)
    for user_id in expired_user_ids:
        try:
            await client.delete_user_password(user_id)
            await remove_zenoh_credential_expiry(user_id)
            logger.info("Removed expired Zenoh credential for user %s", user_id)
        except Exception:
            logger.exception("Failed to remove expired credential for user %s", user_id)


async def run_checker() -> None:
    try:
        while True:
            await remove_expired_usrpwds()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    finally:
        await close_http_client()


def main() -> None:
    try:
        asyncio.run(run_checker())
    except KeyboardInterrupt:
        logger.info("Expired Zenoh credential checker stopped")


if __name__ == "__main__":
    main()
