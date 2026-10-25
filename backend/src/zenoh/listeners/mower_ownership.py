"""Authenticated removal and transfer of registered mowers."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import verify_firebase_id_token
from src.services.mower import update_mower_ownership_service
from src.zenoh.generated import (
    RemoveMowerFromUserRequest,
    RemoveMowerFromUserResponse,
    TransferMowerRequest,
    TransferMowerResponse,
)
from src.zenoh.generated.paths import remove_mower_from_user_path, transfer_mower_path

REMOVE_MOWER_KEY_EXPR = remove_mower_from_user_path()
TRANSFER_MOWER_KEY_EXPR = transfer_mower_path()


async def remove_mower(payload: RemoveMowerFromUserRequest, db: AsyncSession):
    identity = await verify_firebase_id_token(payload.id_token)
    user_id = identity["user_id"]
    await update_mower_ownership_service(user_id, None, payload.mower_id, db)
    return RemoveMowerFromUserResponse(
        message="Mower removed from your account",
        user_id=user_id,
        mower_id=payload.mower_id,
    )


async def transfer_mower(payload: TransferMowerRequest, db: AsyncSession):
    identity = await verify_firebase_id_token(payload.id_token)
    user_id = identity["user_id"]
    await update_mower_ownership_service(
        user_id, payload.new_owner_id, payload.mower_id, db
    )
    return TransferMowerResponse(
        message="Mower transferred successfully",
        user_id=user_id,
        mower_id=payload.mower_id,
        new_owner_id=payload.new_owner_id,
    )
