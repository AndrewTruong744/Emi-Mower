"""User-login query listener for the Zenoh interface."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user import user_login_service
from src.zenoh.generated import UserData, UserLoginRequest, UserLoginResponse
from src.zenoh.generated.paths import user_login_path

LOGIN_KEY_EXPR = user_login_path()


async def user_login(payload: UserLoginRequest, db: AsyncSession) -> UserLoginResponse:
    """Map the login result to the generated Zenoh response."""
    result = await user_login_service(payload, db)
    return UserLoginResponse(
        user_id=result["user_id"],
        token=result["token"],
        expires_in=result["expires_in"],
        user_data=UserData.model_validate(result["user_data"]),
    )
