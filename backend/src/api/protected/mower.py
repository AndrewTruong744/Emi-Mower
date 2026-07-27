import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.protected.schemas import (
    GetMowerDataResponse,
    UpdateMowerNameRequest,
    UpdateMowerNameResponse,
    UpdateMowerOwnershipRequest,
    UpdateMowerOwnershipResponse,
)
from src.config import get_db
from src.services import (
    get_mower_data_service,
    update_mower_name_service,
    update_mower_ownership_service,
    verify_gcp_identity,
)

logger = logging.getLogger("api.mower")
router = APIRouter()


@router.get("/data", response_model=GetMowerDataResponse)
async def get_mower_data_endpoint(
    mower_id: str,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> GetMowerDataResponse:
    """
    GET route to retrieve details of a specific mower.
    mower_id is provided via query parameter ?mower_id=...
    Ensures that the authenticated user owns the mower through mower service.
    """
    logger.info(f"GET /mower/data endpoint triggered for mower {mower_id}")
    user_id = id_token.get("uid") or id_token.get("user_id")

    result = await get_mower_data_service(user_id=user_id, mower_id=mower_id, db=db)
    return GetMowerDataResponse(
        message="Mower data retrieved successfully",
        mower_data=result,
    )


@router.patch("/name", response_model=UpdateMowerNameResponse)
async def update_mower_name_endpoint(
    payload: UpdateMowerNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> UpdateMowerNameResponse:
    """
    PATCH route to update the name/nickname of a mower.
    Requires ownership verification.
    """
    logger.info(f"PATCH /mower/name endpoint triggered for mower {payload.mower_id}")
    user_id = id_token.get("uid") or id_token.get("user_id")

    await update_mower_name_service(
        user_id=user_id,
        mower_id=payload.mower_id,
        new_name=payload.new_name,
        db=db,
    )
    return UpdateMowerNameResponse(
        message="Mower name updated successfully",
        mower_id=payload.mower_id,
        new_name=payload.new_name,
    )


@router.patch("/ownership", response_model=UpdateMowerOwnershipResponse)
async def update_mower_ownership_endpoint(
    payload: UpdateMowerOwnershipRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> UpdateMowerOwnershipResponse:
    """
    PATCH route to update mower ownership.
    Calls update_mower_ownership_service and returns 200, 403, or 500 status code.
    """
    logger.info(
        f"PATCH /mower/ownership endpoint triggered for mower {payload.mower_id}"
    )
    current_owner_id = id_token.get("uid") or id_token.get("user_id")

    await update_mower_ownership_service(
        current_owner_id=current_owner_id,
        new_owner_id=payload.new_owner_id,
        mower_id=payload.mower_id,
        db=db,
    )
    return UpdateMowerOwnershipResponse(
        message="Mower ownership updated successfully",
        mower_id=payload.mower_id,
        new_owner_id=payload.new_owner_id,
    )
