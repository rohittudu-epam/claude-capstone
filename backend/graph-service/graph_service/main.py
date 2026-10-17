from fastapi import FastAPI

from graph_service.routes import router
from shared.health import create_health_router
from shared.observability import init_service

app = FastAPI(title="LinkNote graph-service")
init_service(app, "graph-service")
app.include_router(create_health_router("graph-service"))
app.include_router(router)
