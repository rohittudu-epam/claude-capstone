"""/health (liveness) and /ready (dependency readiness) endpoints."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.db import get_db
from shared.redis_client import create_redis

logger = logging.getLogger(__name__)


def create_health_router(service: str, *, check_redis: bool = False) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": service}

    @router.get("/ready")
    def ready(db: Session = Depends(get_db)) -> JSONResponse:
        checks: dict[str, str] = {}
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            logger.warning("readiness: database check failed", exc_info=True)
            checks["database"] = "unavailable"
        if check_redis:
            try:
                create_redis().ping()
                checks["redis"] = "ok"
            except Exception:
                logger.warning("readiness: redis check failed", exc_info=True)
                checks["redis"] = "unavailable"
        ok = all(value == "ok" for value in checks.values())
        return JSONResponse(
            status_code=200 if ok else 503,
            content={"status": "ready" if ok else "not_ready", "service": service, "checks": checks},
        )

    return router
