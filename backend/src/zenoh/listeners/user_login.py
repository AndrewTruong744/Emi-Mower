"""User-login query listener for the Zenoh interface."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user import user_login_service
from src.zenoh.generated import UserLoginRequest, UserLoginResponse

LOGIN_KEY_EXPR = "user/login"


async def user_login(
    payload: UserLoginRequest, db: AsyncSession
) -> UserLoginResponse:
    """Delegate the generated Zenoh request to the login service."""
    return await user_login_service(payload, db)
