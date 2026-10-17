from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from note_service import service
from note_service.schemas import (
    NoteCreate,
    NoteOut,
    NotePage,
    NoteSummary,
    NoteUpdate,
    SearchHit,
    SearchPage,
    TagOut,
)
from shared.auth import get_current_user_id
from shared.db import get_db
from shared.models import Note
from shared.tags import parse_tag_filter

MAX_QUERY_LENGTH = 200

notes_router = APIRouter(prefix="/api/notes", tags=["notes"])
tags_router = APIRouter(prefix="/api/tags", tags=["tags"])

UserId = Annotated[UUID, Depends(get_current_user_id)]
Db = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def _tag_filter(raw: list[str]) -> list[str]:
    try:
        return parse_tag_filter(raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid tags filter: {exc}") from None


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")


def _note_out(note: Note) -> NoteOut:
    return NoteOut(
        id=note.id,
        owner_id=note.owner_id,
        title=note.title,
        body=note.body,
        tags=[tag.name for tag in note.tags],
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@notes_router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, user_id: UserId, db: Db) -> NoteOut:
    return _note_out(service.create_note(db, user_id, payload))


@notes_router.get("", response_model=NotePage)
def list_notes(
    user_id: UserId,
    db: Db,
    limit: Limit = 20,
    offset: Offset = 0,
    tags: Annotated[list[str], Query()] = [],  # noqa: B006 (FastAPI copies the default)
) -> NotePage:
    notes, total = service.list_notes(db, user_id, tag_names=_tag_filter(tags), limit=limit, offset=offset)
    items = [
        NoteSummary(
            id=n.id, title=n.title, tags=[t.name for t in n.tags], created_at=n.created_at, updated_at=n.updated_at
        )
        for n in notes
    ]
    return NotePage(items=items, total=total, limit=limit, offset=offset)


@notes_router.get("/search", response_model=SearchPage)
def search_notes(
    user_id: UserId,
    db: Db,
    q: Annotated[str, Query(max_length=MAX_QUERY_LENGTH)],
    limit: Limit = 20,
    offset: Offset = 0,
    tags: Annotated[list[str], Query()] = [],  # noqa: B006
) -> SearchPage:
    query = q.strip()
    if not query:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Query parameter 'q' must not be empty")
    results, total = service.search_notes(
        db, user_id, query=query, tag_names=_tag_filter(tags), limit=limit, offset=offset
    )
    items = [
        SearchHit(
            id=n.id, owner_id=n.owner_id, title=n.title, tags=[t.name for t in n.tags], updated_at=n.updated_at, rank=r
        )
        for n, r in results
    ]
    return SearchPage(items=items, total=total, limit=limit, offset=offset)


@notes_router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: UUID, user_id: UserId, db: Db) -> NoteOut:
    try:
        return _note_out(service.get_note(db, user_id, note_id))
    except service.NoteNotFoundError:
        raise _not_found() from None


@notes_router.put("/{note_id}", response_model=NoteOut)
def update_note(note_id: UUID, payload: NoteUpdate, user_id: UserId, db: Db) -> NoteOut:
    try:
        return _note_out(service.update_note(db, user_id, note_id, payload))
    except service.NoteNotFoundError:
        raise _not_found() from None


@notes_router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, user_id: UserId, db: Db) -> Response:
    try:
        service.delete_note(db, user_id, note_id)
    except service.NoteNotFoundError:
        raise _not_found() from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@tags_router.get("", response_model=list[TagOut])
def list_tags(user_id: UserId, db: Db) -> list[TagOut]:
    return [TagOut(id=tag.id, name=tag.name, note_count=count) for tag, count in service.list_tags(db, user_id)]
