"""Note business logic. Every query is scoped to `owner_id`; foreign notes look like missing notes."""

from uuid import UUID, uuid4

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from note_service.schemas import NoteCreate, NoteUpdate
from shared.events import NoteEventType
from shared.models import Note, NoteTag, Tag
from shared.outbox import add_note_event
from shared.tags import note_ids_with_all_tags
from shared.timeutil import utcnow


class NoteNotFoundError(Exception):
    pass


def get_or_create_tags(db: Session, owner_id: UUID, names: list[str]) -> list[Tag]:
    if not names:
        return []
    now = utcnow()
    db.execute(
        pg_insert(Tag)
        .values([{"id": uuid4(), "owner_id": owner_id, "name": name, "created_at": now} for name in names])
        .on_conflict_do_nothing(index_elements=["owner_id", "name"])
    )
    return list(db.scalars(select(Tag).where(Tag.owner_id == owner_id, Tag.name.in_(names)).order_by(Tag.name)))


def _owned_note_stmt(owner_id: UUID, note_id: UUID) -> Select[Note]:
    return select(Note).where(Note.id == note_id, Note.owner_id == owner_id).options(selectinload(Note.tags))


def get_note(db: Session, owner_id: UUID, note_id: UUID) -> Note:
    note = db.scalar(_owned_note_stmt(owner_id, note_id))
    if note is None:
        raise NoteNotFoundError
    return note


def create_note(db: Session, owner_id: UUID, data: NoteCreate) -> Note:
    now = utcnow()
    note = Note(owner_id=owner_id, title=data.title, body=data.body, created_at=now, updated_at=now)
    note.tags = get_or_create_tags(db, owner_id, data.tags)
    db.add(note)
    db.flush()
    add_note_event(db, note_id=note.id, owner_id=owner_id, event_type=NoteEventType.CREATED, occurred_at=now)
    db.commit()
    return note


def update_note(db: Session, owner_id: UUID, note_id: UUID, data: NoteUpdate) -> Note:
    note = db.scalar(_owned_note_stmt(owner_id, note_id).with_for_update())
    if note is None:
        raise NoteNotFoundError

    content_changed = data.title != note.title or data.body != note.body
    tags_changed = False
    if data.tags is not None:
        new_tags = get_or_create_tags(db, owner_id, data.tags)
        if {tag.id for tag in new_tags} != {tag.id for tag in note.tags}:
            note.tags = new_tags
            tags_changed = True

    if content_changed:
        note.title, note.body = data.title, data.body
    if content_changed or tags_changed:
        note.updated_at = utcnow()
    if content_changed:
        # Tag-only edits do not change what link analysis reads, so they emit no event.
        add_note_event(
            db, note_id=note.id, owner_id=owner_id, event_type=NoteEventType.UPDATED, occurred_at=note.updated_at
        )
    db.commit()
    return note


def delete_note(db: Session, owner_id: UUID, note_id: UUID) -> None:
    note = db.scalar(select(Note).where(Note.id == note_id, Note.owner_id == owner_id).with_for_update())
    if note is None:
        raise NoteNotFoundError
    add_note_event(db, note_id=note.id, owner_id=owner_id, event_type=NoteEventType.DELETED, occurred_at=utcnow())
    db.delete(note)
    db.commit()


def list_notes(db: Session, owner_id: UUID, *, tag_names: list[str], limit: int, offset: int) -> tuple[list[Note], int]:
    base = select(Note).where(Note.owner_id == owner_id)
    if tag_names:
        base = base.where(Note.id.in_(note_ids_with_all_tags(owner_id, tag_names)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    notes = db.scalars(
        base.order_by(Note.updated_at.desc(), Note.id).limit(limit).offset(offset).options(selectinload(Note.tags))
    ).all()
    return list(notes), total


def search_notes(
    db: Session, owner_id: UUID, *, query: str, tag_names: list[str], limit: int, offset: int
) -> tuple[list[tuple[Note, float]], int]:
    tsquery = func.websearch_to_tsquery(literal_column("'english'::regconfig"), query)
    matches = Note.search_vector.op("@@")(tsquery)
    base = select(Note).where(Note.owner_id == owner_id, matches)
    if tag_names:
        base = base.where(Note.id.in_(note_ids_with_all_tags(owner_id, tag_names)))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rank = func.ts_rank(Note.search_vector, tsquery).label("rank")
    rows = db.execute(
        base.add_columns(rank)
        .order_by(rank.desc(), Note.updated_at.desc(), Note.id)
        .limit(limit)
        .offset(offset)
        .options(selectinload(Note.tags))
    ).all()
    return [(note, float(score)) for note, score in rows], total


def list_tags(db: Session, owner_id: UUID) -> list[tuple[Tag, int]]:
    rows = db.execute(
        select(Tag, func.count(NoteTag.note_id))
        .outerjoin(NoteTag, NoteTag.tag_id == Tag.id)
        .where(Tag.owner_id == owner_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
    ).all()
    return [(tag, int(count)) for tag, count in rows]
