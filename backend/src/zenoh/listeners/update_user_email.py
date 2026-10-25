"""Zenoh query listener for updating the authenticated user's email."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_firebase_id_token
from src.services.user import update_user_email_service
from src.zenoh.generated import UpdateUserEmailRequest, UpdateUserEmailResponse
from src.zenoh.generated.paths import update_user_email_path

UPDATE_USER_EMAIL_KEY_EXPR = update_user_email_path()


async def update_user_email(
    payload: UpdateUserEmailRequest, db: AsyncSession
) -> UpdateUserEmailResponse:
    """Verify both Google identities and transfer the account and its mowers."""
    identity = await verify_firebase_id_token(payload.id_token)
    user_id = identity["user_id"]

    result = await update_user_email_service(user_id, payload.new_id_token, db=db)
    return UpdateUserEmailResponse(
        message="Google account switched successfully",
        user_id=result["user_id"],
        new_email=result["new_email"],
    )
