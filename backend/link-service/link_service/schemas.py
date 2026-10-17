from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel

from shared.timeutil import as_utc

UTCDatetime = Annotated[datetime, AfterValidator(as_utc)]


class NoteRef(BaseModel):
    id: UUID
    title: str


class SuggestionOut(BaseModel):
    id: UUID
    source_note: NoteRef
    target_note: NoteRef
    similarity_score: float
    explanation: str
    created_at: UTCDatetime


class SuggestionPage(BaseModel):
    items: list[SuggestionOut]
    total: int
    limit: int
    offset: int


class LinkOut(BaseModel):
    id: UUID
    source_note: NoteRef
    target_note: NoteRef
    created_at: UTCDatetime


class LinkPage(BaseModel):
    items: list[LinkOut]
    total: int
    limit: int
    offset: int
