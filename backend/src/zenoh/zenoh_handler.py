"""Async-safe Zenoh query handling with RFC 9457 error responses."""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, RootModel
from pydantic import ValidationError as PydanticValidationError

import zenoh
from src.config.database import AsyncSessionLocal
from src.exceptions import BaseAppException
from src.zenoh.generated import ProblemDetails

logger = logging.getLogger("zenoh.query_handler")
QueryFunction = Callable[[Any, Any], Awaitable[Any]]
KeyedQueryFunction = Callable[[Any, Any, str], Awaitable[Any]]
MessageFunction = Callable[[Any, Any], Awaitable[None]]


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

    if isinstance(error, (PydanticValidationError, ValueError)):
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


class ZenohQueryHandler:
    """Bridge Zenoh's synchronous callback thread to the backend event loop."""

    def __init__(self, session: zenoh.Session, loop: asyncio.AbstractEventLoop):
        self.session = session
        self.loop = loop
        self.queryables: list[Any] = []

    def declare(
        self,
        key_expr: str,
        handler: QueryFunction | KeyedQueryFunction,
        *,
        request_model: type[BaseModel] | None = None,
        include_query_key: bool = False,
    ) -> Any:
        def on_query(query: zenoh.Query) -> None:
            future = asyncio.run_coroutine_threadsafe(
                self._process(query, handler, request_model, include_query_key),
                self.loop,
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
        handler: QueryFunction | KeyedQueryFunction,
        request_model: type[BaseModel] | None,
        include_query_key: bool = False,
    ) -> None:
        instance = str(query.key_expr)
        try:
            raw = _payload_bytes(query.payload)
            request = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(request, dict):
                raise ValueError("Query payload must be a JSON object")
            if request_model is not None:
                request = request_model.model_validate(request)

            async with AsyncSessionLocal() as db:
                if include_query_key:
                    response = await handler(request, db, instance)  # type: ignore[call-arg]
                else:
                    response = await handler(request, db)  # type: ignore[call-arg]
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


class ZenohMessageHandler:
    """Bridge Zenoh subscriber callbacks to the backend event loop.

    Messages use Zenoh's one-way pub/sub pattern: processing failures are
    logged locally because there is no query reply channel for the sender.
    """

    def __init__(self, session: zenoh.Session, loop: asyncio.AbstractEventLoop):
        self.session = session
        self.loop = loop
        self.subscribers: list[Any] = []

    def declare(
        self,
        key_expr: str,
        handler: MessageFunction,
        *,
        message_model: type[BaseModel] | None = None,
    ) -> Any:
        def on_message(sample: zenoh.Sample) -> None:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._process(sample, handler, message_model), self.loop
                )
            except Exception:
                logger.exception("Failed to schedule Zenoh message for %s", key_expr)
                return
            future.add_done_callback(
                lambda completed: self._log_failure(completed, key_expr)
            )

        subscriber = self.session.declare_subscriber(key_expr, on_message)
        self.subscribers.append(subscriber)
        return subscriber

    @staticmethod
    def _log_failure(future: Any, key_expr: str) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Zenoh message failed for %s", key_expr)

    async def _process(
        self,
        sample: zenoh.Sample,
        handler: MessageFunction,
        message_model: type[BaseModel] | None,
    ) -> None:
        raw = _payload_bytes(sample.payload)
        message = json.loads(raw.decode("utf-8")) if raw else {}
        accepts_root_model = message_model is not None and issubclass(
            message_model, RootModel
        )
        if not isinstance(message, dict) and not accepts_root_model:
            raise ValueError("Message payload must be a JSON object")
        if message_model is not None:
            message = message_model.model_validate(message)

        async with AsyncSessionLocal() as db:
            await handler(message, db)

    def close(self) -> None:
        for subscriber in self.subscribers:
            subscriber.undeclare()
        self.subscribers.clear()
