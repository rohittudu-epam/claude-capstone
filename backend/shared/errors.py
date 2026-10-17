"""Uniform error responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Deliberately omits the offending input so passwords and note content never reach responses or logs.
        errors = [
            {"field": ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(status_code=400, content={"detail": "Invalid request", "errors": errors})

    @app.exception_handler(OperationalError)
    async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
        # The driver message can contain connection details, so log the type only and return a fixed body.
        logger.error("database unavailable", extra={"error": type(exc.orig).__name__})
        return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable"})
