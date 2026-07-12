import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.services.auth import verify_gcp_identity
from src.services.user_service import (
    create_user_service,
    get_user_data_service,
    update_user_email_service,
    update_user_name_service,
)

logger = logging.getLogger("api.user_route")
router = APIRouter()


@router.post("/{user_id}/data")
async def create_user_data_endpoint(
    user_id: str,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    POST route to initialize/create a user profile.
    Ensures that the authenticated user matches the path user_id.
    """
    logger.info(f"POST /user/{user_id}/data endpoint triggered")

    token_uid = id_token.get("uid") or id_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            "Auth token UID '%s' does not match path '%s'",
            token_uid,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot create data for a different user",
        )

    result = await create_user_service(id_token)

    if result == "fail":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to create user data",
                "user_data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "User data created successfully",
            "user_data": result,
        },
    )


@router.get("/{user_id}/data")
async def get_user_data_endpoint(
    user_id: str,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    GET route to retrieve a user profile.
    Ensures that the authenticated user matches the path user_id.
    """
    logger.info(f"GET /user/{user_id}/data endpoint triggered")

    token_uid = id_token.get("uid") or id_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            "Auth token UID '%s' does not match path '%s'",
            token_uid,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot access data for a different user",
        )

    result = await get_user_data_service(user_id)

    if result == "fail":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to retrieve user data",
                "user_data": None,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "User data retrieved successfully",
            "user_data": result,
        },
    )


class UpdateUserEmailRequest(BaseModel):
    new_id_token: str


@router.patch("/{user_id}/email")
async def update_user_email_endpoint(
    user_id: str,
    payload: UpdateUserEmailRequest,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    PATCH route to update user email.
    Validates that the authenticated user matches the path,
    calls user service, and returns 200, 403, or 500 status code.
    """
    logger.info(f"PATCH /user/{user_id}/email endpoint triggered")

    token_uid = id_token.get("uid") or id_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            "Auth token UID '%s' does not match path '%s'",
            token_uid,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot update email for a different user",
        )

    result = await update_user_email_service(user_id, payload.new_id_token)

    if result == "not allowed":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": "Not allowed to update email",
                "user_id": user_id,
                "new_email": None,
            },
        )
    elif result == "success":
        # Retrieve the updated user data to get the new email
        user_data = await get_user_data_service(user_id)
        new_email = (
            user_data.get("email") if isinstance(user_data, dict) else None
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User email updated successfully",
                "user_id": user_id,
                "new_email": new_email,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to update user email",
                "user_id": user_id,
                "new_email": None,
            },
        )


class UpdateUserNameRequest(BaseModel):
    new_user_name: str


@router.patch("/{user_id}/name")
async def update_user_name_endpoint(
    user_id: str,
    payload: UpdateUserNameRequest,
    id_token: dict = Depends(verify_gcp_identity),
):
    """
    PATCH route to update user name.
    Validates that the authenticated user matches the path,
    calls user service, and returns 200, 403, or 500 status code.
    """
    logger.info(f"PATCH /user/{user_id}/name endpoint triggered")

    token_uid = id_token.get("uid") or id_token.get("user_id")
    if not token_uid or token_uid != user_id:
        logger.warning(
            "Auth token UID '%s' does not match path '%s'",
            token_uid,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot update name for a different user",
        )

    result = await update_user_name_service(user_id, payload.new_user_name)

    if result == "not allowed":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "message": "Not allowed to update user name",
                "user_id": user_id,
                "new_user_name": None,
            },
        )
    elif result == "success":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "User name updated successfully",
                "user_id": user_id,
                "new_user_name": payload.new_user_name,
            },
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Failed to update user name",
                "user_id": user_id,
                "new_user_name": None,
            },
        )



