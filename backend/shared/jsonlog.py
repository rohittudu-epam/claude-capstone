"""Structured JSON logging with correlation ids and secret redaction.

Rules this module enforces:
- One JSON object per line on stdout: timestamp, level, service, logger, message, correlation_id, extras.
- Extra fields whose names suggest secrets or content (password, token, cookie, authorization, body, ...)
  are replaced with "[redacted]", whatever the caller passes.
- Exception messages from SQLAlchemy are never logged: they embed the bound SQL parameters (emails,
  password hashes, note text). Only the exception type and code locations are written for those.
"""

import json
import logging
import re
import sys
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

SENSITIVE_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "credential",
    "body",
    "content",
)
REDACTED = "[redacted]"
_VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}
_HANDLER_MARK = "_linknote_json_handler"


def new_correlation_id() -> str:
    return uuid4().hex


def valid_correlation_id(value: str | None) -> str | None:
    return value if value and _VALID_CORRELATION_ID.match(value) else None


def current_correlation_id() -> str | None:
    return correlation_id_var.get()


@contextmanager
def correlation_context(correlation_id: str | None) -> Iterator[str]:
    """Binds a correlation id (a fresh one if none is given) for the duration of the block."""
    cid = valid_correlation_id(correlation_id) or new_correlation_id()
    token = correlation_id_var.set(cid)
    try:
        yield cid
    finally:
        correlation_id_var.reset(token)


def is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS)


def describe_exception(exc: BaseException, tb: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"type": f"{type(exc).__module__}.{type(exc).__qualname__}"}
    if isinstance(exc, SQLAlchemyError):
        orig = getattr(exc, "orig", None)
        if orig is not None:
            info["driver_error"] = type(orig).__name__
            sqlstate = getattr(orig, "sqlstate", None)
            if sqlstate:
                info["sqlstate"] = sqlstate
    else:
        info["message"] = str(exc)[:500]
    info["frames"] = [
        f"{f.filename.split('site-packages')[-1].strip('/\\')}:{f.lineno} in {f.name}" for f in traceback.extract_tb(tb)
    ][-12:]
    return info


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            entry[key] = REDACTED if is_sensitive(key) else value
        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = describe_exception(record.exc_info[1], record.exc_info[2])
        return json.dumps(entry, default=str, ensure_ascii=False)


def configure_logging(service: str, level: str = "INFO") -> None:
    """Route all logging, including uvicorn's, through the JSON formatter. Safe to call repeatedly."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARK, False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    setattr(handler, _HANDLER_MARK, True)
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    access = logging.getLogger("uvicorn.access")  # replaced by RequestLoggingMiddleware, which omits query strings
    access.handlers.clear()
    access.propagate = False
