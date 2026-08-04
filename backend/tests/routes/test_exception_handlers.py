from unittest.mock import Mock

import pytest
from fastapi import FastAPI

from src.exception_handlers import register_exception_handlers
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


@pytest.fixture
def registered_app():
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.mark.parametrize(
    ("exception", "status_code"),
    [
        (AuthenticationError("bad auth"), 401),
        (ValidationError("bad input"), 400),
        (ForbiddenError("denied"), 403),
        (NotFoundError("missing"), 404),
        (ExternalServiceError("downstream"), 502),
        (RepositoryError("database"), 500),
        (TokenGenerationError("jwt"), 500),
        (BaseAppException("unexpected"), 500),
    ],
)
async def test_exception_handler_maps_domain_error_to_http_response(
    registered_app, exception, status_code
):
    handler = registered_app.exception_handlers[type(exception)]

    response = await handler(Mock(), exception)

    assert response.status_code == status_code
