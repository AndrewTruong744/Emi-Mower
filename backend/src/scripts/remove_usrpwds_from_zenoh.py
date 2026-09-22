"""Remove expired dynamically provisioned Zenoh user credentials."""

import asyncio
import logging
import time

from src.config.http_client import close_http_client
from src.services.zenoh_credentials import remove_expired_zenoh_credentials

CHECK_INTERVAL_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.remove_usrpwds_from_zenoh")


async def main() -> None:
    """Remove expired Zenoh credentials every 60 seconds."""
    try:
        while True:
            await remove_expired_zenoh_credentials(int(time.time()))
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    finally:
        await close_http_client()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Expired Zenoh credential checker stopped")
