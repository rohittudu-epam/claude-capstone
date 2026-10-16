"""Transactional outbox: events are written in the same transaction as the change they describe."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from shared.events import EVENT_SCHEMA_VERSION, NoteEvent, NoteEventType
from shared.models import OutboxEntry


def add_note_event(
    db: Session, *, note_id: UUID, owner_id: UUID, event_type: NoteEventType, occurred_at: datetime
) -> OutboxEntry:
    event = NoteEvent(
        event_id=uuid4(),
        schema_version=EVENT_SCHEMA_VERSION,
        event_type=event_type,
        note_id=note_id,
        owner_id=owner_id,
        occurred_at=occurred_at,
    )
    entry = OutboxEntry(
        id=event.event_id,
        note_id=note_id,
        owner_id=owner_id,
        event_type=event_type.value,
        payload=event.model_dump_json(),
        schema_version=str(EVENT_SCHEMA_VERSION),
    )
    db.add(entry)
    return entry
