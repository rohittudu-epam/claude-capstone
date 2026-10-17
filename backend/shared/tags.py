"""Tag normalization and the AND-semantics tag filter, shared by note-service and graph-service."""

from uuid import UUID

from sqlalchemy import Select, func, select

from shared.models import NoteTag, Tag

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


def parse_tag_filter(raw: list[str]) -> list[str]:
    """Accepts `?tags=a,b` and/or repeated `?tags=a&tags=b`. Raises ValueError on a bad tag."""
    return normalize_tags([piece for value in raw for piece in value.split(",") if piece.strip()])


def note_ids_with_all_tags(owner_id: UUID, tag_names: list[str]) -> Select[UUID]:
    """Subquery of the owner's note ids carrying every one of `tag_names`."""
    return (
        select(NoteTag.note_id)
        .join(Tag, Tag.id == NoteTag.tag_id)
        .where(Tag.owner_id == owner_id, Tag.name.in_(tag_names))
        .group_by(NoteTag.note_id)
        .having(func.count(Tag.id.distinct()) == len(tag_names))
    )
