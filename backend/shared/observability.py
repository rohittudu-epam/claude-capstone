"""Per-service observability setup: logging, request correlation, request logs, and error bodies."""

import logging
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shared.config import get_settings
from shared.jsonlog import (
    configure_logging,
    correlation_id_var,
    new_correlation_id,
    valid_correlation_id,
)

logger = logging.getLogger("request")

CORRELATION_HEADER = "x-correlation-id"
QUIET_PATHS = {"/health", "/ready"}  # polled constantly by Docker; logged at DEBUG only


class RequestLoggingMiddleware:
    """Assigns a correlation id, echoes it as X-Correlation-ID, and logs one line per request.

    The log line carries method, path, status and duration, never the query string (it can hold
    credentials, e.g. /api/auth/verify?token=...), headers, or bodies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope["headers"]).get(CORRELATION_HEADER.encode(), b"").decode("latin-1")
        correlation_id = valid_correlation_id(incoming) or new_correlation_id()
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        token = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_header(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = message.setdefault("headers", [])
                if not any(name.lower() == CORRELATION_HEADER.encode() for name, _ in headers):
                    headers.append((CORRELATION_HEADER.encode(), correlation_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        except Exception:
            logger.exception("unhandled error", extra={"method": scope["method"], "path": scope["path"]})
            raise
        finally:
            level = logging.DEBUG if scope["path"] in QUIET_PATHS and status_code < 400 else logging.INFO
            logger.log(
                level,
                "request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            correlation_id_var.reset(token)


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None) or correlation_id_var.get()


def _error(request: Request, status_code: int, detail: Any, **extra: Any) -> JSONResponse:
    cid = _correlation_id(request)
    headers = {CORRELATION_HEADER: cid} if cid else {}
    return JSONResponse(
        status_code=status_code, content={"detail": detail, **extra, "correlation_id": cid}, headers=headers
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Deliberately omits the offending input so passwords and note content never reach responses or logs.
        errors = [
            {"field": ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return _error(request, 400, "Invalid request", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        response = _error(request, exc.status_code, exc.detail)
        for name, value in (exc.headers or {}).items():
            response.headers[name] = value
        return response

    @app.exception_handler(OperationalError)
    async def database_unavailable(request: Request, exc: OperationalError) -> JSONResponse:
        logger.error("database unavailable", extra={"error": type(exc.orig).__name__})
        return _error(request, 503, "Service temporarily unavailable")

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception) -> JSONResponse:
        return _error(request, 500, "Internal server error")  # details were logged by the middleware


def init_service(app: FastAPI, service: str) -> None:
    """Logging, correlation ids, request logs, and uniform error responses for one service."""
    configure_logging(service, get_settings().log_level)
    app.add_middleware(RequestLoggingMiddleware)
    install_error_handlers(app)
