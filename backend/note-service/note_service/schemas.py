from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from shared.config import get_settings
from shared.timeutil import as_utc

UTCDatetime = Annotated[datetime, AfterValidator(as_utc)]

MAX_TITLE_LENGTH = 500
MAX_TAG_LENGTH = 50
MAX_TAGS_PER_NOTE = 20


def normalize_tag(raw: str) -> str:
    """Lowercase, trim, and collapse internal whitespace to single spaces."""
    return " ".join(raw.lower().split())


def normalize_tags(raw_tags: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for raw in raw_tags:
        tag = normalize_tag(raw)
        if not tag:
            raise ValueError("tags must not be blank")
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"tags must be at most {MAX_TAG_LENGTH} characters")
        seen.setdefault(tag)
    return list(seen)


class NoteContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    body: str

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value

    @field_validator("body")
    @classmethod
    def _body_size(cls, value: str) -> str:
        limit = get_settings().note_max_body_bytes
        if len(value.encode()) > limit:
            raise ValueError(f"body must be at most {limit} bytes")
        return value


class NoteCreate(NoteContent):
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_NOTE)

    @field_validator("tags")
    @classmethod
    def _normalise(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)


class NoteUpdate(NoteContent):
    """Full replacement of title and body. `tags` omitted leaves tags unchanged; `[]` clears them."""

    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS_PER_NOTE)

    @field_validator("tags")
    @classmethod
    def _normalise(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else normalize_tags(value)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    title: str
    body: str
    tags: list[str]
    created_at: UTCDatetime
    updated_at: UTCDatetime


class NoteSummary(BaseModel):
    id: UUID
    title: str
    tags: list[str]
    created_at: UTCDatetime
    updated_at: UTCDatetime


class NotePage(BaseModel):
    items: list[NoteSummary]
    total: int
    limit: int
    offset: int


class SearchHit(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    tags: list[str]
    updated_at: UTCDatetime
    rank: float


class SearchPage(BaseModel):
    items: list[SearchHit]
    total: int
    limit: int
    offset: int


class TagOut(BaseModel):
    id: UUID
    name: str
    note_count: int
