"""Zenoh query listener for updating the authenticated user's name."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_zenoh_google_id_token
from src.services.user import update_user_name_service
from src.zenoh.generated import UpdateUserNameRequest, UpdateUserNameResponse

UPDATE_USER_NAME_KEY_EXPR = "user/update_name"


async def update_user_name(
    payload: UpdateUserNameRequest, db: AsyncSession
) -> UpdateUserNameResponse:
    """Update the name belonging to the authenticated user."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")

    await update_user_name_service(user_id, payload.new_user_name, db=db)
    return UpdateUserNameResponse(
        message="User name updated successfully",
        user_id=user_id,
        new_user_name=payload.new_user_name,
    )
