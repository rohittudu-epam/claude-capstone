from fastapi import FastAPI

from link_service.routes import links_router, suggestions_router
from shared.errors import install_error_handlers
from shared.health import create_health_router

app = FastAPI(title="LinkNote link-service")
install_error_handlers(app)
app.include_router(create_health_router("link-service", check_redis=True))
app.include_router(suggestions_router)
app.include_router(links_router)
