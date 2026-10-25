"""Provision ACLs for all users and mowers already in PostgreSQL."""

import asyncio
import logging

from src.config.database import AsyncSessionLocal
from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import UserNotFoundError
from src.repositories.account_switch import user_authorization_snapshot
from src.repositories.get_all_mowers_and_users import get_all_mowers_and_users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.add_all_acls")


async def add_all_acls() -> None:
    async with AsyncSessionLocal() as db:
        access_map = await get_all_mowers_and_users(db)

    client = ZenohAdminClient()

    for user in access_map["users"]:
        # A full inventory can become stale while an account switch commits.
        # Serialize permission publication against that switch and login.
        async with AsyncSessionLocal() as db:
            try:
                _, mower_ids = await user_authorization_snapshot(user["user_id"], db)
            except UserNotFoundError:
                await client.retire_user(user["user_id"])
                continue
            await client.configure_user_app(
                user_id=user["user_id"], mower_ids=mower_ids
            )
            await db.commit()
        logger.info(
            "Configured ACL for user %s (%d mower(s))", user["user_id"], len(mower_ids)
        )

    for mower in access_map["mowers"]:
        await client.configure_mower_device(mower["mower_id"])
        logger.info("Configured ACL for mower %s", mower["mower_id"])

    logger.info(
        "Finished ACL bootstrap: %d users, %d mowers",
        len(access_map["users"]),
        len(access_map["mowers"]),
    )


async def _main() -> None:
    from src.config.http_client import close_http_client

    try:
        await add_all_acls()
    finally:
        await close_http_client()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
