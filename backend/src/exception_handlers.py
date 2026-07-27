import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.exceptions import (
    AuthenticationError,
    BaseAppException,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RepositoryError,
    TokenGenerationError,
    ValidationError,
)

logger = logging.getLogger("exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom application exception handlers on the FastAPI app instance according to the standard exception mapping."""

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ):
        logger.warning(f"Authentication failure: {exc}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_error_handler(request: Request, exc: ForbiddenError):
        logger.warning(f"Forbidden operation: {exc}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        logger.warning(f"Resource not found error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ):
        logger.error(f"External service error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "External service error encountered"},
        )

    @app.exception_handler(RepositoryError)
    async def repository_error_handler(request: Request, exc: RepositoryError):
        logger.error(f"Repository error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server database error"},
        )

    @app.exception_handler(TokenGenerationError)
    async def token_generation_error_handler(
        request: Request, exc: TokenGenerationError
    ):
        logger.error(f"Token generation error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Failed to generate authentication token"},
        )

    @app.exception_handler(BaseAppException)
    async def base_app_exception_handler(request: Request, exc: BaseAppException):
        logger.error(f"Unhandled application exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected application error occurred"},
        )
