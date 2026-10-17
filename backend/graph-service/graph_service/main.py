from fastapi import FastAPI

from graph_service.routes import router
from shared.errors import install_error_handlers
from shared.health import create_health_router

app = FastAPI(title="LinkNote graph-service")
install_error_handlers(app)
app.include_router(create_health_router("graph-service"))
app.include_router(router)
