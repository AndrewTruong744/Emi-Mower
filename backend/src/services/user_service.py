import logging
import random
import string

import httpx
from fastapi.security import HTTPAuthorizationCredentials

from src.repositories.create_user import create_user
from src.repositories.get_mowers_of_user import (
    get_mowers_of_user,
)
from src.repositories.get_user_data import get_user_data
from src.repositories.update_user_email import update_user_email
from src.repositories.update_user_name import update_user_name
from src.services.auth import verify_gcp_identity
from src.services.temp_jwt import generate_jwt_token

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
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=new_id_token)
        decoded_token = await verify_gcp_identity(cred)
    except Exception as verify_err:
        logger.warning(f"Failed to verify ID token for user email update: {verify_err}")
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


async def get_zenoh_jwt_service(user_id: str) -> str:
    """
    Generates a JWT token for the user, uses user_id as key and JWT token as password,
    and calls http://127.0.0.1:8001 to update the auth userpwd password store.
    Calls get_mowers_of_user to get the list of mowers owned by the user
    and configures ACL rules, subject, and policy for /mower/{mower_id} routes.
    Returns the JWT token string or "fail".
    """
    logger.info(f"get_zenoh_jwt_service called for user: {user_id}")

    try:
        # 1. Retrieve list of mowers owned by user
        mowers_res = await get_mowers_of_user(user_id)
        if mowers_res == "fail":
            logger.error(f"Failed to retrieve mowers for user: {user_id}")
            return "fail"

        mower_ids = []
        if isinstance(mowers_res, list):
            for item in mowers_res:
                if isinstance(item, dict) and "id" in item:
                    mower_ids.append(str(item["id"]))
                else:
                    mower_ids.append(str(item))

        # 2. Generate JWT token
        jwt_token = generate_jwt_token(user_id)
        if not jwt_token:
            logger.error(f"Failed to generate JWT token for user: {user_id}")
            return "fail"

        # 3. Call http://127.0.0.1:8001 to update Zenoh usrpwd & ACL
        zenoh_url = "http://127.0.0.1:8001"
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Add user_id as key and jwt token as password to usrpwd password store
            pwd_resp = await client.put(
                f"{zenoh_url}/config/transport/auth/usrpwd/passwords/{user_id}",
                content=jwt_token,
                headers={"Content-Type": "text/plain"},
            )
            if pwd_resp.status_code >= 400:
                logger.warning(
                    f"Zenoh usrpwd PUT returned status {pwd_resp.status_code},"
                    " retrying with json..."
                )
                await client.put(
                    f"{zenoh_url}/config/transport/auth/usrpwd/{user_id}",
                    json={"username": user_id, "password": jwt_token},
                )

            # Add ACL rules for each mower owned by user
            rule_ids = []
            for mower_id in mower_ids:
                rule_id = f"rule_{user_id}_{mower_id}"
                rule_ids.append(rule_id)
                rule_payload = {
                    "id": rule_id,
                    "key_expr": f"/mower/{mower_id}/**",
                    "permission": "allow",
                }
                await client.put(
                    f"{zenoh_url}/config/access_control/rules/{rule_id}",
                    json=rule_payload,
                )

            # Add ACL subject for user
            subject_id = f"subject_{user_id}"
            subject_payload = {
                "id": subject_id,
                "usernames": [user_id],
            }
            await client.put(
                f"{zenoh_url}/config/access_control/subjects/{subject_id}",
                json=subject_payload,
            )

            # Add ACL policy linking subject and rules
            policy_id = f"policy_{user_id}"
            policy_payload = {
                "id": policy_id,
                "subjects": [subject_id],
                "rules": rule_ids,
            }
            await client.put(
                f"{zenoh_url}/config/access_control/policies/{policy_id}",
                json=policy_payload,
            )

        return jwt_token
    except Exception as err:
        logger.error(
            f"Failed to generate Zenoh JWT / configure ACL for user {user_id}: {err}",
            exc_info=True,
        )
        return "fail"