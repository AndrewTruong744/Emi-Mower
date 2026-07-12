import logging
import random
import string

from fastapi.security import HTTPAuthorizationCredentials

from src.repositories.create_user import create_user
from src.repositories.get_user_data import get_user_data
from src.repositories.update_user_email import update_user_email
from src.repositories.update_user_name import update_user_name
from src.services.auth import verify_gcp_identity

logger = logging.getLogger("services.user_service")


async def create_user_service(id_token: dict) -> dict | str:
    """
    Service to handle user registration/account creation.
    Extracts user_id, email, and name from the decoded id_token dict.
    If name is not present, generates a random 8-character alphanumeric string.
    Returns the user data dict or "fail".
    """
    logger.info("create_user_service called")

    # Firebase decoded ID token stores the user ID in the 'uid' claim
    user_id = id_token.get("uid") or id_token.get("user_id")
    email = id_token.get("email")
    name = id_token.get("name")

    if not user_id:
        logger.error("Missing 'uid' or 'user_id' in id_token claims.")
        return "fail"

    if not email:
        logger.error("Missing 'email' in id_token claims.")
        return "fail"

    if not name:
        name = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        logger.info(f"Name missing in id_token; generated random name: {name}")

    return await create_user(user_id=user_id, email=email, name=name)


async def get_user_data_service(user_id: str) -> dict | str:
    """
    Service to retrieve a user's data by delegating to get_user_data repo.
    Returns the user data dict or "fail".
    """
    logger.info(f"get_user_data_service called for user: {user_id}")
    return await get_user_data(user_id)


async def update_user_email_service(user_id: str, new_id_token: str) -> str:
    """
    Service to update the email of a user.
    Verifies the new_id_token using verify_gcp_identity,
    ensures it matches the requested user_id, and updates PostgreSQL.
    Returns "success", "not allowed", or "fail".
    """
    logger.info(f"update_user_email_service called for user: {user_id}")

    try:
        # Utilize verify_gcp_identity to verify and decode the token
        cred = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=new_id_token
        )
        decoded_token = await verify_gcp_identity(cred)
    except Exception as verify_err:
        logger.warning(
            f"Failed to verify ID token for user email update: {verify_err}"
        )
        return "not allowed"

    # Verify that the token claims match the user_id we are trying to update
    token_uid = decoded_token.get("uid") or decoded_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            f"Token UID '{token_uid}' does not match target user_id '{user_id}'"
        )
        return "not allowed"

    new_email = decoded_token.get("email")
    if not new_email:
        logger.error("Verified ID token lacks 'email' claim")
        return "fail"

    return await update_user_email(user_id, new_email)


async def update_user_name_service(user_id: str, new_user_name: str) -> str:
    """
    Service to update the name of a user.
    First ensures the name is alphanumeric, then calls update_user_name CRUD.
    Returns "success", "not allowed", or "fail".
    """
    logger.info(
        f"update_user_name_service called for user: {user_id}, name: {new_user_name}"
    )

    # Ensure that the name is alphanumeric
    if not new_user_name.isalnum():
        logger.warning(
            f"User name update rejected: '{new_user_name}' is not alphanumeric."
        )
        return "fail"

    return await update_user_name(user_id, new_user_name)


