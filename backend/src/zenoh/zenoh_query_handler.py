"""Async-safe Zenoh query handling with RFC 9457 error responses."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import jwt
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

import zenoh
from src.config.database import AsyncSessionLocal
from src.config.settings import settings
from src.exceptions import AuthenticationError, BaseAppException
from src.zenoh.generated import ProblemDetails

logger = logging.getLogger("zenoh.query_handler")
QueryFunction = Callable[[Any, Any], Awaitable[Any]]


def _payload_bytes(payload: Any) -> bytes:
    if payload is None:
        return b""
    if hasattr(payload, "to_bytes"):
        return payload.to_bytes()
    return bytes(payload)


def _problem_detail(
    *, status: int, title: str, detail: str, code: str, instance: str
) -> ProblemDetails:
    return ProblemDetails(
        type=f"https://emi-mower.dev/problems/{code}",
        title=title,
        status=status,
        detail=detail,
        instance=instance,
        code=code,
        timestamp=datetime.now(timezone.utc),
    )


def _exception_problem(error: Exception, instance: str) -> ProblemDetails:
    if isinstance(error, BaseAppException):
        name = error.__class__.__name__
        mapping = {
            "AuthenticationError": (
                401,
                "Authentication failed",
                "authentication-failed",
            ),
            "ValidationError": (400, "Invalid request", "invalid-request"),
            "UserNotFoundError": (404, "User not found", "user-not-found"),
            "MowerNotFoundError": (404, "Mower not found", "mower-not-found"),
            "ForbiddenError": (403, "Forbidden", "forbidden"),
            "OwnershipError": (403, "Ownership check failed", "ownership-failed"),
            "RepositoryError": (500, "Repository failure", "repository-failure"),
            "ExternalServiceError": (
                502,
                "External service failure",
                "external-service-failure",
            ),
            "TokenGenerationError": (
                500,
                "Token generation failed",
                "token-generation-failed",
            ),
        }
        status, title, code = mapping.get(
            name, (500, "Application error", "application-error")
        )
        return _problem_detail(
            status=status,
            title=title,
            detail=str(error),
            code=code,
            instance=instance,
        )

    if isinstance(error, PydanticValidationError):
        return _problem_detail(
            status=400,
            title="Invalid request",
            detail=str(error),
            code="invalid-request",
            instance=instance,
        )

    logger.exception("Unhandled Zenoh query exception")
    return _problem_detail(
        status=500,
        title="Internal server error",
        detail="The request could not be completed",
        code="internal-error",
        instance=instance,
    )


def validate_application_jwt(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the JWT returned by ``user/login`` in an application request."""
    value = payload.get("jwt") or payload.get("authorization")
    if isinstance(value, str) and value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not isinstance(value, str) or not value:
        raise AuthenticationError("A Zenoh application JWT is required")
    try:
        claims = jwt.decode(value, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as err:
        raise AuthenticationError("Invalid, expired, or tampered Zenoh JWT") from err
    if not claims.get("sub"):
        raise AuthenticationError("Zenoh JWT does not contain a subject")
    return claims


class ZenohQueryHandler:
    """Bridge Zenoh's synchronous callback thread to the backend event loop."""

    def __init__(self, session: zenoh.Session, loop: asyncio.AbstractEventLoop):
        self.session = session
        self.loop = loop
        self.queryables: list[Any] = []

    def declare(
        self,
        key_expr: str,
        handler: QueryFunction,
        *,
        request_model: type[BaseModel] | None = None,
        requires_jwt: bool = True,
    ) -> Any:
        def on_query(query: zenoh.Query) -> None:
            future = asyncio.run_coroutine_threadsafe(
                self._process(query, handler, request_model, requires_jwt), self.loop
            )
            try:
                future.result(timeout=30)
            except Exception:
                logger.exception("Zenoh query failed for %s", key_expr)

        queryable = self.session.declare_queryable(key_expr, on_query)
        self.queryables.append(queryable)
        return queryable

    async def _process(
        self,
        query: zenoh.Query,
        handler: QueryFunction,
        request_model: type[BaseModel] | None,
        requires_jwt: bool,
    ) -> None:
        instance = str(query.key_expr)
        try:
            raw = _payload_bytes(query.payload)
            request = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(request, dict):
                raise ValueError("Query payload must be a JSON object")
            if requires_jwt:
                request["_claims"] = validate_application_jwt(request)
            if request_model is not None:
                request = request_model.model_validate(request)

            async with AsyncSessionLocal() as db:
                response = await handler(request, db)
            if isinstance(response, BaseModel):
                response_payload = response.model_dump_json()
            else:
                response_payload = json.dumps(response)
            query.reply(query.key_expr, response_payload.encode("utf-8"))
        except Exception as error:
            problem = _exception_problem(error, instance)
            query.reply_err(problem.model_dump_json().encode("utf-8"))

    def close(self) -> None:
        for queryable in self.queryables:
            queryable.undeclare()
        self.queryables.clear()
