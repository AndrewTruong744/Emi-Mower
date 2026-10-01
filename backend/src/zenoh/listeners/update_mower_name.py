"""Zenoh query listener for updating an owned mower's name."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_firebase_id_token
from src.services.mower import mower_route_params, update_mower_name_service
from src.zenoh.generated import UpdateMowerNameRequest, UpdateMowerNameResponse
from src.zenoh.generated.paths import update_mower_name_path

UPDATE_MOWER_NAME_KEY_EXPR = update_mower_name_path("*")


async def update_mower_name(
    payload: UpdateMowerNameRequest, db: AsyncSession, key_expr: str
) -> UpdateMowerNameResponse:
    """Update a mower name after authenticating and authorizing its owner."""
    identity = await verify_firebase_id_token(payload.id_token)
    user_id = identity["user_id"]
    (mower_id,) = mower_route_params(key_expr, UPDATE_MOWER_NAME_KEY_EXPR)

    await update_mower_name_service(
        user_id=user_id,
        mower_id=mower_id,
        new_name=payload.new_name,
        db=db,
    )
    return UpdateMowerNameResponse(
        message="Mower name updated successfully",
        mower_id=mower_id,
        new_name=payload.new_name,
    )
