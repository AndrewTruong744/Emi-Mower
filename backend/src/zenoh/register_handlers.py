"""Register the backend's Zenoh handler declarations."""

from src.zenoh.generated import UserLoginRequest
from src.zenoh.listeners import LOGIN_KEY_EXPR, user_login
from src.zenoh.zenoh_handler import ZenohQueryHandler


def register_handlers(query_handler: ZenohQueryHandler) -> None:
    """Declare the request/reply handlers served by this backend."""
    query_handler.declare(
        LOGIN_KEY_EXPR,
        user_login,
        request_model=UserLoginRequest,
    )
