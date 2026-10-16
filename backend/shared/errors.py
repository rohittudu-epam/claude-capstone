"""Uniform error responses."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Deliberately omits the offending input so passwords and note content never reach responses or logs.
        errors = [
            {"field": ".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(status_code=400, content={"detail": "Invalid request", "errors": errors})
