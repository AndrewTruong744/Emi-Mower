import logging
import random
import string
import time

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import ZenohAdminClient
from src.exceptions import (
    AuthenticationError,
    ForbiddenError,
    UserNotFoundError,
    ValidationError,
)
from src.repositories import (
    create_user,
    get_mowers_of_user,
    get_user_data,
    record_zenoh_credential_expiry,
    update_user_email,
    update_user_name,
)
from src.services.auth import verify_gcp_identity
from src.services.temp_jwt import generate_jwt_token
from src.zenoh.generated import UserData, UserLoginRequest, UserLoginResponse

ZENOH_JWT_TTL_SECONDS = 5 * 60

logger = logging.getLogger("services.user")


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


async def user_login_service(
    payload: UserLoginRequest, db: AsyncSession
) -> UserLoginResponse:
    """Process a generated Zenoh login request and return its wire response."""
    firebase_token = payload.id_token
    if not firebase_token:
        raise ValidationError("The login payload must contain a non-empty id_token")

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=firebase_token
    )
    decoded_identity = await verify_gcp_identity(credentials)
    user_id = decoded_identity.get("uid") or decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")

    try:
        user_data = await get_user_data(user_id, db=db)
    except UserNotFoundError:
        user_data = await create_user_service(decoded_identity, db=db)

    mower_ids = await get_mowers_of_user(user_id, db=db)
    token = generate_jwt_token(user_id, exp_seconds=ZENOH_JWT_TTL_SECONDS)
    await ZenohAdminClient().configure_user_app(
        user_id=user_id,
        mower_ids=mower_ids,
        password=token,
    )

    expires_at = int(time.time()) + ZENOH_JWT_TTL_SECONDS
    await record_zenoh_credential_expiry(user_id, expires_at)
    return UserLoginResponse(
        user_id=user_id,
        token=token,
        expires_in=ZENOH_JWT_TTL_SECONDS,
        user_data=UserData.model_validate(user_data),
    )


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
    Service to update the nickname/user name of a user.
    Verifies that the new name is alphanumeric and non-empty.
    Raises ValidationError, UserNotFoundError, or RepositoryError.
    """
    logger.info(
        f"update_user_name_service called for user: {user_id}, name: {new_user_name}"
    )

    if not new_user_name or not new_user_name.isalnum():
        logger.warning(
            f"User name update rejected: '{new_user_name}' is not alphanumeric."
        )
        raise ValidationError(f"User name '{new_user_name}' is not alphanumeric")

    await update_user_name(user_id, new_user_name, db=db)


async def get_zenoh_jwt_service(user_id: str, db: AsyncSession) -> str:
    """
    Generates a JWT token for the user.
    Returns the JWT token string or raises TokenGenerationError.
    """
    logger.info(f"get_zenoh_jwt_service called for user: {user_id}")

    mower_ids = await get_mowers_of_user(user_id, db=db)
    jwt_value = generate_jwt_token(user_id, exp_seconds=ZENOH_JWT_TTL_SECONDS)
    await ZenohAdminClient().configure_user_app(
        user_id=user_id,
        mower_ids=mower_ids,
        password=jwt_value,
    )
    expires_at = int(time.time()) + ZENOH_JWT_TTL_SECONDS
    await record_zenoh_credential_expiry(user_id, expires_at)
    return jwt_value
