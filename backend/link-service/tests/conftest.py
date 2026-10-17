from uuid import uuid4

import pytest
from sqlalchemy import select, update

from link_service.processing import make_event_handler
from shared.config import get_settings
from shared.events import NoteEvent, NoteEventType
from shared.models import Note, Suggestion
from shared.timeutil import utcnow

K8S_TITLE = "Kubernetes deployment strategies"
K8S_BODY = "rolling updates for kubernetes deployment pods and services with health probes"


@pytest.fixture
def alice(make_user):
    return make_user("alice@example.com")


@pytest.fixture
def bob(make_user):
    return make_user("bob@example.com")


@pytest.fixture
def add_note(session_factory):
    def _add(owner, title=K8S_TITLE, body=K8S_BODY) -> Note:
        now = utcnow()
        with session_factory() as db:
            note = Note(owner_id=owner.id, title=title, body=body, created_at=now, updated_at=now)
            db.add(note)
            db.commit()
        return note

    return _add


@pytest.fixture
def edit_note(session_factory):
    def _edit(note, **changes) -> None:
        with session_factory() as db:
            db.execute(update(Note).where(Note.id == note.id).values(updated_at=utcnow(), **changes))
            db.commit()

    return _edit


@pytest.fixture
def process(session_factory):
    def _process(note, owner, event_type=NoteEventType.UPDATED, **settings_overrides) -> None:
        settings = get_settings().model_copy(update=settings_overrides)
        event = NoteEvent(
            event_id=uuid4(),
            schema_version=1,
            event_type=event_type,
            note_id=note.id,
            owner_id=owner.id,
            occurred_at=utcnow(),
        )
        make_event_handler(session_factory, settings)(event)

    return _process


@pytest.fixture
def suggestions(session_factory):
    def _all() -> list[Suggestion]:
        with session_factory() as db:
            return list(db.scalars(select(Suggestion).order_by(Suggestion.created_at, Suggestion.id)))

    return _all
