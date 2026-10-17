"""Note event contract (schema version 1) shared by publisher and consumers.

Payloads carry identifiers and timestamps only, never note content. For created/updated events
`occurred_at` equals the note's `updated_at`, so it doubles as the note version. `correlation_id`
is optional and links worker logs to the request that caused the event. Consumers must
ignore unknown fields so the contract can grow within a schema version.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

STREAM_NOTE_EVENTS = "note_events"
STREAM_NOTE_EVENTS_DEAD = "note_events:dead"
EVENT_SCHEMA_VERSION = 1


class EventSchemaError(ValueError):
    """The stream entry is malformed or uses a schema version this code cannot read."""


class NoteEventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class NoteEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    schema_version: int
    event_type: NoteEventType
    note_id: UUID
    owner_id: UUID
    occurred_at: datetime
    correlation_id: str | None = None

    def to_stream_fields(self) -> dict[str, str]:
        fields = {
            "event_id": str(self.event_id),
            "schema_version": str(self.schema_version),
            "event_type": self.event_type.value,
            "note_id": str(self.note_id),
            "owner_id": str(self.owner_id),
            "occurred_at": self.occurred_at.isoformat(),
        }
        if self.correlation_id:
            fields["correlation_id"] = self.correlation_id
        return fields

    @classmethod
    def from_stream_fields(cls, fields: dict[str, str]) -> NoteEvent:
        try:
            event = cls.model_validate(fields)
        except ValidationError as exc:
            raise EventSchemaError("malformed note event") from exc
        if event.schema_version != EVENT_SCHEMA_VERSION:
            raise EventSchemaError(f"unsupported event schema_version {event.schema_version}")
        return event
