"""Provision ACLs for all users and mowers already in PostgreSQL."""

import asyncio
import logging

from src.config.database import AsyncSessionLocal
from src.config.http_client import close_http_client
from src.config.zenoh_client import ZenohAdminClient
from src.repositories.get_all_mowers_and_users import get_all_mowers_and_users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.add_all_acls")


async def add_all_acls() -> None:
    try:
        async with AsyncSessionLocal() as db:
            access_map = await get_all_mowers_and_users(db)

        client = ZenohAdminClient()

        for user in access_map["users"]:
            await client.configure_user_app(
                user_id=user["user_id"],
                mower_ids=user["mower_ids"],
            )
            logger.info(
                "Configured ACL for user %s (%d mower(s))",
                user["user_id"],
                len(user["mower_ids"]),
            )

        for mower in access_map["mowers"]:
            await client.configure_mower_device(mower["mower_id"])
            logger.info("Configured ACL for mower %s", mower["mower_id"])

        logger.info(
            "Finished ACL bootstrap: %d users, %d mowers",
            len(access_map["users"]),
            len(access_map["mowers"]),
        )
    finally:
        await close_http_client()


def main() -> None:
    asyncio.run(add_all_acls())


if __name__ == "__main__":
    main()
