from fastapi import FastAPI

from link_service.routes import links_router, suggestions_router
from shared.health import create_health_router
from shared.observability import init_service

app = FastAPI(title="LinkNote link-service")
init_service(app, "link-service")
app.include_router(create_health_router("link-service", check_redis=True))
app.include_router(suggestions_router)
app.include_router(links_router)
