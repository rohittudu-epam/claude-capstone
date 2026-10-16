from fastapi import FastAPI

from note_service.routes import notes_router, tags_router
from shared.errors import install_error_handlers
from shared.health import create_health_router

app = FastAPI(title="LinkNote note-service")
install_error_handlers(app)
app.include_router(create_health_router("note-service", check_redis=True))
app.include_router(notes_router)
app.include_router(tags_router)
