import logging

from src.repositories.add_mower_to_user import add_mower_to_user
from src.repositories.check_mower_ownership import check_mower_ownership
from src.repositories.get_mower_data import get_mower_data
from src.repositories.update_mower_name import update_mower_name
from src.repositories.verify_ownership import verify_ownership

logger = logging.getLogger("services.mower_service")


async def get_mower_data_service(user_id: str, mower_id: str) -> dict | str:
    """
    Service to retrieve a specific mower's data for a user.
    Calls get_mower_data to fetch all mowers owned by the user
    and returns the one matching mower_id.
    Returns the mower data dict or "fail".
    """
    logger.info(
        f"get_mower_data_service called for user {user_id}, mower {mower_id}"
    )

    mowers = await get_mower_data(user_id)
    if mowers == "fail":
        return "fail"

    # Find the specific mower by ID (which verifies ownership implicitly)
    for mower in mowers:
        if mower.get("id") == mower_id:
            return mower

    logger.warning(
        f"User {user_id} does not own mower {mower_id} or mower does not exist"
    )
    return "fail"


async def update_mower_name_service(
    user_id: str, mower_id: str, new_name: str
) -> str:
    """
    Service to update the nickname of a mower.
    First verifies ownership, then checks that the new name is alphanumeric,
    and finally calls update_mower_name repository.
    Returns "success", "not allowed", or "fail".
    """
    logger.info(
        "update_mower_name_service called for user %s, mower %s, name %s",
        user_id,
        mower_id,
        new_name,
    )

    # 1. Verify alphanumeric format
    if not new_name.isalnum():
        logger.warning(
            f"Nickname update rejected: '{new_name}' is not alphanumeric."
        )
        return "fail"

    # 2. Verify ownership
    is_owner = await verify_ownership(user_id, mower_id)
    if not is_owner:
        logger.warning(
            "Ownership verification failed: User %s does not own mower %s",
            user_id,
            mower_id,
        )
        return "not allowed"

    # 3. Call repository to update DB and cache
    return await update_mower_name(mower_id, new_name)


async def update_mower_ownership_service(
    current_owner_id: str | None,
    new_owner_id: str | None,
    mower_id: str,
) -> str:
    """
    Service to update/transfer mower ownership.
    Checks the actual owner first. If none exists, adds new_owner_id.
    If an owner exists, verifies it matches current_owner_id before transferring.
    Returns "success", "not_allowed", or "fail".
    """
    logger.info(
        "update_mower_ownership_service: current=%s, new=%s, mower=%s",
        current_owner_id,
        new_owner_id,
        mower_id,
    )

    actual_owner = await check_mower_ownership(mower_id)
    if actual_owner == "fail":
        return "fail"

    # If there is no owner, automatically add new_owner_id
    if actual_owner is None:
        logger.info(
            "Mower %s has no current owner. Assigning to: %s",
            mower_id,
            new_owner_id,
        )
        return await add_mower_to_user(new_owner_id, mower_id)

    # If there is an owner, verify current_owner_id matches actual_owner
    if current_owner_id != actual_owner:
        logger.warning(
            "Transfer rejected: specified owner %s != actual %s",
            current_owner_id,
            actual_owner,
        )
        return "not_allowed"

    logger.info(
        "Transferring mower %s ownership from %s to: %s",
        mower_id,
        current_owner_id,
        new_owner_id,
    )
    return await add_mower_to_user(new_owner_id, mower_id)


