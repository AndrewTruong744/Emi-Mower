"""Zenoh query listener for updating an owned mower's name."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import ValidationError
from src.services.auth import verify_zenoh_google_id_token
from src.services.mower import update_mower_name_service
from src.zenoh.generated import UpdateMowerNameRequest, UpdateMowerNameResponse

UPDATE_MOWER_NAME_KEY_EXPR = "mower/*/update_name"


def _mower_id_from_query_key(key_expr: str) -> str:
    """Extract the mower ID from ``mower/{mower_id}/update_name``."""
    parts = str(key_expr).split("/")
    if (
        len(parts) != 3
        or parts[0] != "mower"
        or not parts[1]
        or parts[2] != "update_name"
    ):
        raise ValidationError("Invalid mower name update query path")
    return parts[1]


async def update_mower_name(
    payload: UpdateMowerNameRequest, db: AsyncSession, key_expr: str
) -> UpdateMowerNameResponse:
    """Update a mower name after authenticating and authorizing its owner."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")
    mower_id = _mower_id_from_query_key(key_expr)

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
