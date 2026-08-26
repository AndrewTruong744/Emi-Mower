"""Zenoh query listener for assigning an unowned mower to the caller."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_zenoh_google_id_token
from src.services.mower import update_mower_ownership_service
from src.zenoh.generated import AddMowerToUserRequest, AddMowerToUserResponse
from src.zenoh.generated.paths import add_mower_to_user_path

ADD_MOWER_TO_USER_KEY_EXPR = add_mower_to_user_path()


async def add_mower_to_user(
    payload: AddMowerToUserRequest, db: AsyncSession
) -> AddMowerToUserResponse:
    """Assign the requested mower to the authenticated user."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")

    await update_mower_ownership_service(
        current_owner_id=None,
        new_owner_id=user_id,
        mower_id=payload.mower_id,
        db=db,
    )
    return AddMowerToUserResponse(
        message="Mower added to user successfully",
        user_id=user_id,
        mower_id=payload.mower_id,
    )
