import logging
import random
import string

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import (
    AuthenticationError,
    ForbiddenError,
    UserNotFoundError,
    ValidationError,
)
from src.repositories import (
    create_user,
    find_user_by_email,
    get_user_data,
    update_user_email,
    update_user_name,
)
from src.repositories.account_switch import (
    invalidate_account_switch_cache,
    stage_account_switch,
    user_authorization_snapshot,
)
from src.services.auth import verify_firebase_id_token
from src.zenoh.generated import UserLoginRequest

ZENOH_SESSION_TTL_SECONDS = 5 * 60

logger = logging.getLogger("services.user")


async def create_user_service(id_token: dict, db: AsyncSession) -> dict:
    """
    Service to handle user registration/account creation.
    Extracts user_id, email, and name from the decoded id_token dict.
    If name is not present, generates a random 8-character alphanumeric string.
    Returns the user data dict or raises ValidationError / RepositoryError.
    """
    logger.info("create_user_service called")

    user_id = id_token.get("user_id")
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
    payload: UserLoginRequest, db: AsyncSession, connection_context: dict | None = None
) -> dict:
    """Authenticate the user and authorize the captured connection."""
    firebase_token = payload.id_token
    if not firebase_token:
        raise ValidationError("The login payload must contain a non-empty id_token")

    decoded_identity = await verify_firebase_id_token(firebase_token)
    user_id = decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")

    try:
        user_data, mower_ids = await user_authorization_snapshot(user_id, db)
    except UserNotFoundError:
        await create_user_service(decoded_identity, db=db)
        user_data, mower_ids = await user_authorization_snapshot(user_id, db)
    user_data = {**user_data, "mowers": mower_ids}
    if not connection_context:
        raise AuthenticationError("Login requires router-captured connection context")
    admin = ZenohAdminClient()
    await admin.configure_user_app(user_id, mower_ids)
    await admin.authorize_connection(
        user_id, connection_context, ZENOH_SESSION_TTL_SECONDS
    )
    await db.commit()  # Release the account lock after policy publication.
    return {
        "user_id": user_id,
        "authorized": True,
        "expires_in": ZENOH_SESSION_TTL_SECONDS,
        "user_data": user_data,
    }


async def get_user_data_service(user_id: str, db: AsyncSession) -> dict:
    """
    Service to retrieve a user's data by delegating to get_user_data repo.
    Returns the user data dict or raises UserNotFoundError / RepositoryError.
    """
    logger.info(f"get_user_data_service called for user: {user_id}")
    return await get_user_data(user_id, db=db)


async def update_user_email_service(
    user_id: str, new_id_token: str, db: AsyncSession
) -> dict:
    """Verify the destination Google identity and atomically transfer the account."""
    identity = await verify_firebase_id_token(new_id_token)
    target_id, new_email = identity.get("user_id"), identity.get("email")
    if not target_id or not new_email:
        raise ValidationError(
            "The replacement Google identity is missing its UID or email"
        )
    if (
        not identity.get("email_verified")
        or identity.get("firebase", {}).get("sign_in_provider") != "google.com"
    ):
        raise ForbiddenError("Use a verified Google account for the replacement login")
    if target_id == user_id:
        existing = await find_user_by_email(new_email, db=db)
        if existing is not None and existing != user_id:
            raise ValidationError("The email address is already in use")
        await update_user_email(user_id, new_email, db=db)
        return {"user_id": user_id, "new_email": new_email}

    admin = ZenohAdminClient()
    retired = False
    try:
        mower_ids = await stage_account_switch(user_id, target_id, new_email, db)
        # Revoke every old connection's application permissions immediately.
        # Only this already-running operation's reply may leave the old router
        # transport. No query, command, telemetry or subscription remains allowed.
        await admin.retire_user(user_id)
        retired = True
        await invalidate_account_switch_cache(user_id, target_id, mower_ids)
        await db.commit()
    except Exception:
        await db.rollback()
        if retired:
            # Restore only the ownership that still exists after rollback,
            # serialized against another switch/login. Otherwise stay denied.
            try:
                _, owned = await user_authorization_snapshot(user_id, db)
                await admin.configure_user_app(user_id, owned)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.warning("Account switch failed; old session needs a fresh login")
        raise
    # New login independently builds its policy from PostgreSQL. Do not authorize
    # another identity on the old connection; Firebase handoff opens a new one.
    return {"user_id": target_id, "new_email": new_email}


async def update_user_name_service(
    user_id: str, new_user_name: str, db: AsyncSession
) -> str:
    """
    Service to update the nickname/user name of a user.
    Accepts a non-empty, single-line display name up to 64 characters.
    Raises ValidationError, UserNotFoundError, or RepositoryError.
    """
    logger.info(
        f"update_user_name_service called for user: {user_id}, name: {new_user_name}"
    )

    new_user_name = new_user_name.strip()
    if (
        not new_user_name
        or len(new_user_name) > 64
        or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in new_user_name)
    ):
        raise ValidationError(
            "Display name must be 1–64 characters without control characters"
        )

    await update_user_name(user_id, new_user_name, db=db)
    return new_user_name
