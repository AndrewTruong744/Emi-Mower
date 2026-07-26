import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.exceptions import (
    ForbiddenError,
    NotFoundError,
    OwnershipError,
    RepositoryError,
    ValidationError,
)
from src.services.auth import verify_gcp_identity
from src.services.mower_service import (
    get_mower_data_service,
    update_mower_name_service,
    update_mower_ownership_service,
)

logger = logging.getLogger("api.mower_route")
router = APIRouter()


@router.get("/data")
async def get_mower_data_endpoint(
    mower_id: str,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    GET route to retrieve details of a specific mower.
    mower_id is provided via query parameter ?mower_id=...
    Ensures that the authenticated user owns the mower through mower service.
    """
    logger.info(f"GET /mower/data endpoint triggered for mower {mower_id}")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    try:
        result = await get_mower_data_service(user_id=user_id, mower_id=mower_id, db=db)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Mower data retrieved successfully",
                "mower_data": result,
            },
        )
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


class UpdateMowerNameRequest(BaseModel):
    mower_id: str
    new_name: str


@router.patch("/name")
async def update_mower_name_endpoint(
    payload: UpdateMowerNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH route to update the name/nickname of a mower.
    Requires ownership verification.
    """
    logger.info(f"PATCH /mower/name endpoint triggered for mower {payload.mower_id}")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    try:
        await update_mower_name_service(
            user_id=user_id,
            mower_id=payload.mower_id,
            new_name=payload.new_name,
            db=db,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Mower name updated successfully",
                "mower_id": payload.mower_id,
                "new_name": payload.new_name,
            },
        )
    except ValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)
        )
    except ForbiddenError as fb_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(fb_err))
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


class UpdateMowerOwnershipRequest(BaseModel):
    mower_id: str
    new_owner_id: str | None = None


@router.patch("/ownership")
async def update_mower_ownership_endpoint(
    payload: UpdateMowerOwnershipRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH route to update mower ownership.
    Calls update_mower_ownership_service and returns 200, 403, or 500 status code.
    """
    logger.info(
        f"PATCH /mower/ownership endpoint triggered for mower {payload.mower_id}"
    )

    current_owner_id = id_token.get("uid") or id_token.get("user_id")
    if not current_owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID not found in token",
        )

    try:
        await update_mower_ownership_service(
            current_owner_id=current_owner_id,
            new_owner_id=payload.new_owner_id,
            mower_id=payload.mower_id,
            db=db,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Mower ownership updated successfully",
                "mower_id": payload.mower_id,
                "new_owner_id": payload.new_owner_id,
            },
        )
    except OwnershipError as own_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(own_err))
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )
