"""Suggestion review and accepted-link endpoints.

Error policy for a suggestion action:
- 404: the suggestion does not exist, belongs to someone else, or was already accepted or rejected.
- 409: the suggestion is stale because either note changed after it was computed; it is regenerated
  from the new content and will reappear in the pending list if it still qualifies.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from link_service.schemas import LinkOut, LinkPage, NoteRef, SuggestionOut, SuggestionPage
from shared.auth import get_current_user_id
from shared.db import get_db
from shared.links import canonical_pair
from shared.models import AcceptedLink, Note, Suggestion
from shared.timeutil import utcnow

suggestions_router = APIRouter(prefix="/api/suggestions", tags=["suggestions"])
links_router = APIRouter(prefix="/api/links", tags=["links"])

UserId = Annotated[UUID, Depends(get_current_user_id)]
Db = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]

NOT_FOUND = "Suggestion not found, or it was already accepted or rejected"
STALE = "Suggestion is stale because a note changed; it will be regenerated if it still applies"


@suggestions_router.get("", response_model=SuggestionPage)
def list_pending(
    user_id: UserId, db: Db, limit: Limit = 20, offset: Offset = 0, note_id: UUID | None = None
) -> SuggestionPage:
    source, target = aliased(Note), aliased(Note)
    visible = (
        Suggestion.owner_id == user_id,
        Suggestion.status == "pending",
        source.owner_id == user_id,
        target.owner_id == user_id,
        source.updated_at == Suggestion.source_updated_at,  # hide stale suggestions
        target.updated_at == Suggestion.target_updated_at,
    )
    base = (
        select(Suggestion, source.title, target.title)
        .join(source, source.id == Suggestion.source_note_id)
        .join(target, target.id == Suggestion.target_note_id)
        .where(*visible)
    )
    if note_id is not None:
        base = base.where(or_(Suggestion.source_note_id == note_id, Suggestion.target_note_id == note_id))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(Suggestion.similarity_score.desc(), Suggestion.created_at, Suggestion.id)
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        SuggestionOut(
            id=s.id,
            source_note=NoteRef(id=s.source_note_id, title=source_title),
            target_note=NoteRef(id=s.target_note_id, title=target_title),
            similarity_score=s.similarity_score,
            explanation=s.explanation,
            created_at=s.created_at,
        )
        for s, source_title, target_title in rows
    ]
    return SuggestionPage(items=items, total=total, limit=limit, offset=offset)


def _lock_actionable(db: Session, user_id: UUID, suggestion_id: UUID) -> Suggestion:
    """The caller's pending suggestion, row-locked, with ownership and freshness verified."""
    suggestion = db.scalar(
        select(Suggestion)
        .where(Suggestion.id == suggestion_id, Suggestion.owner_id == user_id, Suggestion.status == "pending")
        .with_for_update()
    )
    if suggestion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    notes = {
        n.id: n
        for n in db.scalars(select(Note).where(Note.id.in_([suggestion.source_note_id, suggestion.target_note_id])))
    }
    source, target = notes.get(suggestion.source_note_id), notes.get(suggestion.target_note_id)
    if source is None or target is None or source.owner_id != user_id or target.owner_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if source.updated_at != suggestion.source_updated_at or target.updated_at != suggestion.target_updated_at:
        raise HTTPException(status.HTTP_409_CONFLICT, STALE)
    return suggestion


def _link_out(db: Session, link: AcceptedLink) -> LinkOut:
    note_ids = [link.source_note_id, link.target_note_id]
    titles = dict(db.execute(select(Note.id, Note.title).where(Note.id.in_(note_ids))).all())
    return LinkOut(
        id=link.id,
        source_note=NoteRef(id=link.source_note_id, title=titles[link.source_note_id]),
        target_note=NoteRef(id=link.target_note_id, title=titles[link.target_note_id]),
        created_at=link.created_at,
    )


@suggestions_router.post("/{suggestion_id}/accept", response_model=LinkOut)
def accept(suggestion_id: UUID, response: Response, user_id: UserId, db: Db) -> LinkOut:
    suggestion = _lock_actionable(db, user_id, suggestion_id)
    source_id, target_id = canonical_pair(suggestion.source_note_id, suggestion.target_note_id)
    created = db.execute(
        pg_insert(AcceptedLink)
        .values(source_note_id=source_id, target_note_id=target_id, owner_id=user_id, created_at=utcnow())
        .on_conflict_do_nothing(index_elements=["source_note_id", "target_note_id"])
        .returning(AcceptedLink.id)
    ).scalar_one_or_none()
    link = db.scalar(
        select(AcceptedLink).where(AcceptedLink.source_note_id == source_id, AcceptedLink.target_note_id == target_id)
    )
    assert link is not None
    db.delete(suggestion)
    db.commit()
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return _link_out(db, link)


@suggestions_router.post("/{suggestion_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject(suggestion_id: UUID, user_id: UserId, db: Db) -> Response:
    suggestion = _lock_actionable(db, user_id, suggestion_id)
    suggestion.status = "rejected"
    suggestion.rejected_at = utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@links_router.get("", response_model=LinkPage)
def list_links(user_id: UserId, db: Db, limit: Limit = 20, offset: Offset = 0, note_id: UUID | None = None) -> LinkPage:
    """Accepted links; with `note_id`, those touching that note from either side."""
    base = select(AcceptedLink).where(AcceptedLink.owner_id == user_id)
    if note_id is not None:
        base = base.where(or_(AcceptedLink.source_note_id == note_id, AcceptedLink.target_note_id == note_id))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    links = db.scalars(base.order_by(AcceptedLink.created_at.desc(), AcceptedLink.id).limit(limit).offset(offset)).all()
    return LinkPage(items=[_link_out(db, link) for link in links], total=total, limit=limit, offset=offset)
