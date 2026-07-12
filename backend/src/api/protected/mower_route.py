import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.services.auth import verify_gcp_identity
from src.services.mower_service import (
    get_mower_data_service,
    update_mower_name_service,
    update_mower_ownership_service,
)

logger = logging.getLogger("api.mower_route")
router = APIRouter()


@router.get("/{mower_id}/data")
async def get_mower_data_endpoint(
    mower_id: str,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    GET route to retrieve details of a specific mower.
    Ensures that the authenticated user owns the mower through mower service.
    """
    logger.info(f"GET /mower/{mower_id}/data endpoint triggered")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    result = await get_mower_data_service(user_id=user_id, mower_id=mower_id)

    if result == "fail":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to retrieve mower data",
                "mower_data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Mower data retrieved successfully",
            "mower_data": result,
        },
    )


class UpdateMowerNameRequest(BaseModel):
    new_name: str


@router.patch("/{uuid}/name")
async def update_mower_name_endpoint(
    uuid: str,
    payload: UpdateMowerNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    PATCH route to update the name/nickname of a mower.
    Requires ownership verification.
    """
    logger.info(f"PATCH /mower/{uuid}/name endpoint triggered")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    result = await update_mower_name_service(
        user_id=user_id, mower_id=uuid, new_name=payload.new_name
    )

    if result == "not allowed":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": "Not allowed to modify this mower nickname",
                "mower_id": uuid,
                "new_name": None,
            },
        )
    elif result == "success":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Mower name updated successfully",
                "mower_id": uuid,
                "new_name": payload.new_name,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to update mower nickname",
                "mower_id": uuid,
                "new_name": None,
            },
        )


class UpdateMowerOwnershipRequest(BaseModel):
    new_owner_id: str | None = None


@router.patch("/{mower_id}/ownership")
async def update_mower_ownership_endpoint(
    mower_id: str,
    payload: UpdateMowerOwnershipRequest,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    PATCH route to update mower ownership.
    Calls update_mower_ownership_service and returns 200, 403, or 500 status code.
    """
    logger.info(f"PATCH /mower/{mower_id}/ownership endpoint triggered")

    current_owner_id = id_token.get("uid") or id_token.get("user_id")
    if not current_owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    result = await update_mower_ownership_service(
        current_owner_id=current_owner_id,
        new_owner_id=payload.new_owner_id,
        mower_id=mower_id,
    )

    if result == "not_allowed":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": "Not allowed to transfer ownership of this mower",
                "mower_id": mower_id,
                "new_owner_id": None,
            },
        )
    elif result == "success":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Mower ownership updated successfully",
                "mower_id": mower_id,
                "new_owner_id": payload.new_owner_id,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to update mower ownership",
                "mower_id": mower_id,
                "new_owner_id": None,
            },
        )


