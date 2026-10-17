from fastapi import FastAPI

from auth_service.routes import router
from shared.health import create_health_router
from shared.observability import init_service

app = FastAPI(title="LinkNote auth-service")
init_service(app, "auth-service")
app.include_router(create_health_router("auth-service"))
app.include_router(router)
