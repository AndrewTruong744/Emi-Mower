"""Remove expired dynamically provisioned Zenoh user credentials."""

import asyncio
import logging
import os
import time

from src.config import ZenohAdminClient
from src.config.http_client import close_http_client
from src.config.valkey_client import get_valkey_client
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY

CHECK_INTERVAL_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.remove_usrpwds_from_zenoh")


async def remove_expired_usrpwds() -> None:
    app_rest_url = os.getenv("ZENOH_APP_REST_URL", "http://127.0.0.1:8001")
    client = ZenohAdminClient(base_url=app_rest_url)
    now = int(time.time())

    async with get_valkey_client() as v_client:
        expiry_map = await v_client.hgetall(ZENOH_TOKEN_EXPIRY_KEY)

    for user_id, expires_at in expiry_map.items():
        try:
            is_expired = int(expires_at) <= now
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid expiry for user %s", user_id)
            continue

        if not is_expired:
            continue

        try:
            await client.delete_user_password(user_id)
            async with get_valkey_client() as v_client:
                await v_client.hdel(ZENOH_TOKEN_EXPIRY_KEY, user_id)
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
