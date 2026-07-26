import json
import logging
import random
import string

import httpx
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import (
    ExternalServiceError,
    ForbiddenError,
    ValidationError,
)
from src.repositories.create_user import create_user
from src.repositories.get_mowers_of_user import get_mowers_of_user
from src.repositories.get_user_data import get_user_data
from src.repositories.update_user_email import update_user_email
from src.repositories.update_user_name import update_user_name
from src.services.auth import verify_gcp_identity
from src.services.temp_jwt import generate_jwt_token

logger = logging.getLogger("services.user_service")


async def create_user_service(id_token: dict, db: AsyncSession) -> dict:
    """
    Service to handle user registration/account creation.
    Extracts user_id, email, and name from the decoded id_token dict.
    If name is not present, generates a random 8-character alphanumeric string.
    Returns the user data dict or raises ValidationError / RepositoryError.
    """
    logger.info("create_user_service called")

    # Firebase decoded ID token stores the user ID in the 'uid' claim
    user_id = id_token.get("uid") or id_token.get("user_id")
    email = id_token.get("email")
    name = id_token.get("name")

    if not user_id:
        logger.error("Missing 'uid' or 'user_id' in id_token claims.")
        raise ValidationError("Missing 'uid' or 'user_id' in id_token claims.")

    if not email:
        logger.error("Missing 'email' in id_token claims.")
        raise ValidationError("Missing 'email' in id_token claims.")

    if not name:
        name = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        logger.info(f"Name missing in id_token; generated random name: {name}")

    return await create_user(user_id=user_id, email=email, name=name, db=db)


async def get_user_data_service(user_id: str, db: AsyncSession) -> dict:
    """
    Service to retrieve a user's data by delegating to get_user_data repo.
    Returns the user data dict or raises UserNotFoundError / RepositoryError.
    """
    logger.info(f"get_user_data_service called for user: {user_id}")
    return await get_user_data(user_id, db=db)


async def update_user_email_service(
    user_id: str, new_id_token: str, db: AsyncSession
) -> None:
    """
    Service to update the email of a user.
    Verifies the new_id_token using verify_gcp_identity,
    ensures it matches the requested user_id, and updates PostgreSQL.
    Raises ForbiddenError, ValidationError, UserNotFoundError, or RepositoryError.
    """
    logger.info(f"update_user_email_service called for user: {user_id}")

    try:
        cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=new_id_token)
        decoded_token = await verify_gcp_identity(cred)
    except Exception as verify_err:
        logger.warning(f"Failed to verify ID token for user email update: {verify_err}")
        raise ForbiddenError(
            "Not allowed: ID token verification failed"
        ) from verify_err

    token_uid = decoded_token.get("uid") or decoded_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            f"Token UID '{token_uid}' does not match target user_id '{user_id}'"
        )
        raise ForbiddenError("Not allowed: Token UID does not match target user ID")

    new_email = decoded_token.get("email")
    if not new_email:
        logger.error("Verified ID token lacks 'email' claim")
        raise ValidationError("Verified ID token lacks 'email' claim")

    await update_user_email(user_id, new_email, db=db)


async def update_user_name_service(
    user_id: str, new_user_name: str, db: AsyncSession
) -> None:
    """
    Service to update the name of a user.
    First ensures the name is alphanumeric, then calls update_user_name CRUD.
    Raises ValidationError, UserNotFoundError, or RepositoryError.
    """
    logger.info(
        f"update_user_name_service called for user: {user_id}, name: {new_user_name}"
    )

    if not new_user_name.isalnum():
        logger.warning(
            f"User name update rejected: '{new_user_name}' is not alphanumeric."
        )
        raise ValidationError(f"User name '{new_user_name}' is not alphanumeric")

    await update_user_name(user_id, new_user_name, db=db)


async def get_zenoh_jwt_service(user_id: str, db: AsyncSession) -> str:
    """
    Generates a JWT token for the user, uses user_id as key and JWT token as password.
    Executes 4 targeted individual HTTP PUT requests to Zenoh REST API:
    - dictionary/{user_id}
    - rules/{rule_id}
    - subjects/{subject_id}
    - policies/{policy_id}
    Safely updates user credentials and ACLs without overwriting other users' ACLs.
    Returns the JWT token string or raises ExternalServiceError / RepositoryError.
    """
    logger.info(f"get_zenoh_jwt_service called for user: {user_id}")

    mowers_res = await get_mowers_of_user(user_id, db=db)

    mower_ids = []
    if isinstance(mowers_res, list):
        for item in mowers_res:
            if isinstance(item, dict) and "id" in item:
                mower_ids.append(str(item["id"]))
            else:
                mower_ids.append(str(item))

    jwt_token = generate_jwt_token(user_id)
    if not jwt_token:
        logger.error(f"Failed to generate JWT token for user: {user_id}")
        raise ExternalServiceError(f"Failed to generate JWT token for user: {user_id}")

    rule_id = f"rule_{user_id}"
    subject_id = f"subject_{user_id}"
    policy_id = f"policy_{user_id}"
    key_exprs = [f"mower/{m_id}/**" for m_id in mower_ids]

    zenoh_url = "http://127.0.0.1:8001"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 1. Update usrpwd dictionary specifically for user_id (non-destructive)
            pwd_resp = await client.put(
                f"{zenoh_url}/@/config/transport/auth/usrpwd/dictionary/{user_id}",
                content=json.dumps(jwt_token),
                headers={"Content-Type": "application/json"},
            )
            if pwd_resp.status_code >= 400:
                logger.error(
                    f"Zenoh usrpwd dictionary PUT returned HTTP {pwd_resp.status_code}"
                )
                raise ExternalServiceError(
                    f"Failed to update Zenoh usrpwd: HTTP {pwd_resp.status_code}"
                )

            # 2. Add/update targeted ACL rule for user
            rule_payload = {
                "id": rule_id,
                "permission": "allow",
                "flows": ["ingress", "egress"],
                "messages": [
                    "put",
                    "declare_subscriber",
                    "query",
                    "reply",
                    "delete",
                ],
                "key_exprs": key_exprs,
            }
            rule_resp = await client.put(
                f"{zenoh_url}/@/config/access_control/rules/{rule_id}",
                json=rule_payload,
            )
            if rule_resp.status_code >= 400:
                logger.error(f"Zenoh rule PUT returned HTTP {rule_resp.status_code}")
                raise ExternalServiceError(
                    f"Failed to update Zenoh rule: HTTP {rule_resp.status_code}"
                )

            # 3. Add/update targeted ACL subject for user
            subject_payload = {
                "id": subject_id,
                "usernames": [user_id],
            }
            subject_resp = await client.put(
                f"{zenoh_url}/@/config/access_control/subjects/{subject_id}",
                json=subject_payload,
            )
            if subject_resp.status_code >= 400:
                logger.error(
                    f"Zenoh subject PUT returned HTTP {subject_resp.status_code}"
                )
                raise ExternalServiceError(
                    f"Failed to update Zenoh subject: HTTP {subject_resp.status_code}"
                )

            # 4. Add/update targeted ACL policy linking user subject & rule
            policy_payload = {
                "id": policy_id,
                "subjects": [subject_id],
                "rules": [rule_id],
            }
            policy_resp = await client.put(
                f"{zenoh_url}/@/config/access_control/policies/{policy_id}",
                json=policy_payload,
            )
            if policy_resp.status_code >= 400:
                logger.error(
                    f"Zenoh policy PUT returned HTTP {policy_resp.status_code}"
                )
                raise ExternalServiceError(
                    f"Failed to update Zenoh policy: HTTP {policy_resp.status_code}"
                )

        return jwt_token
    except ExternalServiceError:
        raise
    except Exception as err:
        logger.error(
            f"Failed to generate Zenoh JWT / configure ACL for user {user_id}: {err}",
            exc_info=True,
        )
        raise ExternalServiceError(
            f"Failed to configure Zenoh ACL for user {user_id}"
        ) from err
