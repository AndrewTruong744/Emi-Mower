import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.protected.schemas import (
    CreateUserDataResponse,
    GetUserDataResponse,
    GetZenohTokenResponse,
    UpdateUserEmailRequest,
    UpdateUserEmailResponse,
    UpdateUserNameRequest,
    UpdateUserNameResponse,
)
from src.config import get_db
from src.services import (
    create_user_service,
    get_user_data_service,
    get_zenoh_jwt_service,
    update_user_email_service,
    update_user_name_service,
    verify_gcp_identity,
)

logger = logging.getLogger("api.user")
router = APIRouter()


@router.post("/data", response_model=CreateUserDataResponse)
async def create_user_data_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> CreateUserDataResponse:
    """
    POST route to initialize/create a user profile.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("POST /user/data endpoint triggered")
    result = await create_user_service(id_token, db=db)
    return CreateUserDataResponse(
        message="User data created successfully",
        user_data=result,
    )


@router.get("/data", response_model=GetUserDataResponse)
async def get_user_data_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> GetUserDataResponse:
    """
    GET route to retrieve a user profile.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("GET /user/data endpoint triggered")
    user_id = id_token.get("uid") or id_token.get("user_id")
    result = await get_user_data_service(user_id, db=db)
    return GetUserDataResponse(
        message="User data retrieved successfully",
        user_data=result,
    )


@router.patch("/email", response_model=UpdateUserEmailResponse)
async def update_user_email_endpoint(
    payload: UpdateUserEmailRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> UpdateUserEmailResponse:
    """
    PATCH route to update user email.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("PATCH /user/email endpoint triggered")
    user_id = id_token.get("uid") or id_token.get("user_id")

    await update_user_email_service(user_id, payload.new_id_token, db=db)
    user_data = await get_user_data_service(user_id, db=db)
    new_email = user_data.get("email") if isinstance(user_data, dict) else None

    return UpdateUserEmailResponse(
        message="User email updated successfully",
        user_id=user_id,
        new_email=new_email,
    )


@router.patch("/name", response_model=UpdateUserNameResponse)
async def update_user_name_endpoint(
    payload: UpdateUserNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> UpdateUserNameResponse:
    """
    PATCH route to update user name.
    Uses authenticated user ID from id_token claims.
    """
    logger.info("PATCH /user/name endpoint triggered")
    user_id = id_token.get("uid") or id_token.get("user_id")

    await update_user_name_service(user_id, payload.new_user_name, db=db)
    return UpdateUserNameResponse(
        message="User name updated successfully",
        user_id=user_id,
        new_user_name=payload.new_user_name,
    )


@router.get("/zenoh", response_model=GetZenohTokenResponse)
async def get_zenoh_token_endpoint(
    id_token: dict = Depends(verify_gcp_identity),
    db: AsyncSession = Depends(get_db),
) -> GetZenohTokenResponse:
    """
    GET route to generate and return a Zenoh JWT token for the authenticated user.
    """
    logger.info("GET /zenoh endpoint triggered")
    user_id = id_token.get("uid") or id_token.get("user_id")

    jwt_token = await get_zenoh_jwt_service(user_id, db=db)
    return GetZenohTokenResponse(
        message="Zenoh JWT token generated successfully",
        token=jwt_token,
    )
