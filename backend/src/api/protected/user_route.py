import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.exceptions import (
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RepositoryError,
    ValidationError,
)
from src.services.auth import verify_gcp_identity
from src.services.user_service import (
    create_user_service,
    get_user_data_service,
    get_zenoh_jwt_service,
    update_user_email_service,
    update_user_name_service,
)

logger = logging.getLogger("api.user_route")
router = APIRouter()


@router.post("/data")
async def create_user_data_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    POST route to initialize/create a user profile.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("POST /user/data endpoint triggered")
    try:
        result = await create_user_service(id_token, db=db)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User data created successfully",
                "user_data": result,
            },
        )
    except ValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)
        )
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


@router.get("/data")
async def get_user_data_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    GET route to retrieve a user profile.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("GET /user/data endpoint triggered")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID missing from token",
        )

    try:
        result = await get_user_data_service(user_id, db=db)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User data retrieved successfully",
                "user_data": result,
            },
        )
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


class UpdateUserEmailRequest(BaseModel):
    new_id_token: str


@router.patch("/email")
async def update_user_email_endpoint(
    payload: UpdateUserEmailRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH route to update user email.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("PATCH /user/email endpoint triggered")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID missing from token",
        )

    try:
        await update_user_email_service(user_id, payload.new_id_token, db=db)
        user_data = await get_user_data_service(user_id, db=db)
        new_email = user_data.get("email") if isinstance(user_data, dict) else None
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User email updated successfully",
                "user_id": user_id,
                "new_email": new_email,
            },
        )
    except ForbiddenError as fb_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(fb_err))
    except ValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)
        )
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


class UpdateUserNameRequest(BaseModel):
    new_user_name: str


@router.patch("/name")
async def update_user_name_endpoint(
    payload: UpdateUserNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    PATCH route to update user name.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("PATCH /user/name endpoint triggered")

    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID missing from token",
        )

    try:
        await update_user_name_service(user_id, payload.new_user_name, db=db)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User name updated successfully",
                "user_id": user_id,
                "new_user_name": payload.new_user_name,
            },
        )
    except ValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err)
        )
    except NotFoundError as nf_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(nf_err))
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )


@router.get("/zenoh")
async def get_zenoh_token_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    GET route to generate and return a Zenoh JWT token for the authenticated user.
    Calls user service to generate JWT and configure Zenoh ACL rules/passwords.
    Returns 200 with JWT token or 500 on failure.
    """
    logger.info("GET /zenoh endpoint triggered")
    user_id = id_token.get("uid") or id_token.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: User ID missing from token",
        )

    try:
        jwt_token = await get_zenoh_jwt_service(user_id, db=db)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Zenoh JWT token generated successfully",
                "token": jwt_token,
            },
        )
    except ExternalServiceError as ext_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(ext_err),
        )
    except RepositoryError as repo_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(repo_err),
        )
