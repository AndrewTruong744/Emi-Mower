"""Zenoh query listener for updating the authenticated user's email."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_zenoh_google_id_token
from src.services.user import update_user_email_service
from src.zenoh.generated import UpdateUserEmailRequest, UpdateUserEmailResponse
from src.zenoh.generated.paths import update_user_email_path

UPDATE_USER_EMAIL_KEY_EXPR = update_user_email_path()


async def update_user_email(
    payload: UpdateUserEmailRequest, db: AsyncSession
) -> UpdateUserEmailResponse:
    """Update a user's email using their original and new Google ID tokens."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")

    new_email = await update_user_email_service(
        user_id, payload.new_id_token, db=db
    )
    return UpdateUserEmailResponse(
        message="User email updated successfully",
        user_id=user_id,
        new_email=new_email,
    )
