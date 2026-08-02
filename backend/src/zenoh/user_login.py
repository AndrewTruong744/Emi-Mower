"""User login request handler for the Zenoh query interface."""

import time

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import ZenohAdminClient
from src.config.valkey_client import get_valkey_client
from src.exceptions import AuthenticationError, UserNotFoundError, ValidationError
from src.repositories.get_mowers_of_user import get_mowers_of_user
from src.repositories.get_user_data import get_user_data
from src.schemas.valkey import ZENOH_TOKEN_EXPIRY_KEY
from src.services.auth import verify_gcp_identity
from src.services.temp_jwt import generate_jwt_token
from src.services.user import create_user_service
from src.zenoh.generated import UserData, UserLoginRequest, UserLoginResponse

LOGIN_KEY_EXPR = "user/login"
ZENOH_JWT_TTL_SECONDS = 5 * 60


async def user_login(
    payload: UserLoginRequest, db: AsyncSession
) -> UserLoginResponse:
    """Verify a Firebase ID token and issue the JWT used by Zenoh queries.

    The Firebase ID token is used only for the login exchange.  The returned
    JWT is signed with ``settings.JWT_SECRET`` and is subsequently validated by
    the application query handler.
    """
    firebase_token = payload.id_token
    if not firebase_token:
        raise ValidationError("The login payload must contain a non-empty id_token")

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=firebase_token
    )
    decoded_identity = await verify_gcp_identity(credentials)
    user_id = decoded_identity.get("uid") or decoded_identity.get("user_id")
    if not user_id:
        raise AuthenticationError("Authenticated identity does not contain a user id")

    try:
        user_data = await get_user_data(user_id, db=db)
    except UserNotFoundError:
        user_data = await create_user_service(decoded_identity, db=db)

    mower_ids = await get_mowers_of_user(user_id, db=db)
    jwt_value = generate_jwt_token(user_id, exp_seconds=ZENOH_JWT_TTL_SECONDS)
    await ZenohAdminClient().configure_user_app(
        user_id=user_id,
        mower_ids=mower_ids,
        password=jwt_value,
    )

    expires_at = int(time.time()) + ZENOH_JWT_TTL_SECONDS
    async with get_valkey_client() as v_client:
        await v_client.hset(
            ZENOH_TOKEN_EXPIRY_KEY,
            mapping={user_id: str(expires_at)},
        )

    return UserLoginResponse(
        user_id=user_id,
        token=jwt_value,
        expires_in=ZENOH_JWT_TTL_SECONDS,
        user_data=UserData.model_validate(user_data),
    )
