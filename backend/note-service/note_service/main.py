from fastapi import FastAPI

from note_service.routes import notes_router, tags_router
from shared.health import create_health_router
from shared.observability import init_service

app = FastAPI(title="LinkNote note-service")
init_service(app, "note-service")
app.include_router(create_health_router("note-service", check_redis=True))
app.include_router(notes_router)
app.include_router(tags_router)
