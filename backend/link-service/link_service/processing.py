"""Turns a note event into up-to-date suggestions for that note.

`refresh_suggestions` is a pure function of database state, never of the event payload, so it is
idempotent and tolerant of duplicate or reordered deliveries. It runs in the caller's transaction:
an exception leaves nothing half-written and the event can simply be retried.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from link_service.similarity import BODY_CHARS, explain, keyword_weights, similarity
from shared.config import Settings, get_settings
from shared.events import NoteEvent, NoteEventType
from shared.links import canonical_pair
from shared.models import AcceptedLink, Note, Suggestion
from shared.timeutil import utcnow

logger = logging.getLogger(__name__)

PREFILTER_TERMS = 15


@dataclass(frozen=True)
class Candidate:
    note_id: UUID
    updated_at: datetime
    score: float
    explanation: str


@dataclass(frozen=True)
class RefreshResult:
    skipped: bool = False
    upserted: int = 0
    removed: int = 0
    suppressed: int = 0


def find_candidates(db: Session, note: Note, settings: Settings) -> list[Candidate]:
    """Same-owner notes that clear the score threshold, best first, at most `link_suggestion_max_per_note`.

    Postgres full-text search only narrows the field to notes sharing at least one of the source's
    strongest keywords; the score itself comes from `similarity`.
    """
    weights = keyword_weights(note.title, note.body)
    if not weights:
        return []
    strongest = sorted(weights, key=lambda k: (-weights[k], k))[:PREFILTER_TERMS]
    tsquery = func.to_tsquery("english", " | ".join(strongest))  # tokens are letters/digits only
    rows = db.execute(
        select(Note.id, Note.title, func.left(Note.body, BODY_CHARS), Note.updated_at)
        .where(Note.owner_id == note.owner_id, Note.id != note.id, Note.search_vector.op("@@")(tsquery))
        .order_by(func.ts_rank(Note.search_vector, tsquery).desc(), Note.id)
        .limit(settings.link_candidate_limit)
    ).all()

    scored = []
    for note_id, title, body, updated_at in rows:
        result = similarity(weights, keyword_weights(title, body))
        if result.score >= settings.link_suggestion_threshold and (
            len(result.shared) >= settings.link_suggestion_min_shared_keywords
        ):
            scored.append(Candidate(note_id, updated_at, result.score, explain(result)))
    scored.sort(key=lambda c: (-c.score, c.note_id))
    return scored[: settings.link_suggestion_max_per_note]


def refresh_suggestions(db: Session, note_id: UUID, owner_id: UUID, settings: Settings) -> RefreshResult:
    # A shared lock stops the note changing under us between reading it and writing its suggestions.
    note = db.scalar(select(Note).where(Note.id == note_id).with_for_update(read=True))
    if note is None or note.owner_id != owner_id:
        return RefreshResult(skipped=True)  # deleted since the event, or not this owner's note

    linked = set(
        db.scalars(
            select(AcceptedLink.source_note_id)
            .where(AcceptedLink.target_note_id == note.id)
            .union(select(AcceptedLink.target_note_id).where(AcceptedLink.source_note_id == note.id))
        )
    )
    desired = {c.note_id: c for c in find_candidates(db, note, settings) if c.note_id not in linked}

    existing = db.scalars(
        select(Suggestion)
        .where(or_(Suggestion.source_note_id == note.id, Suggestion.target_note_id == note.id))
        .with_for_update()
    ).all()
    other_ids = {s.target_note_id if s.source_note_id == note.id else s.source_note_id for s in existing}
    versions = dict(db.execute(select(Note.id, Note.updated_at).where(Note.id.in_(other_ids | {note.id}))).all())

    removable: list[UUID] = []
    suppressed = 0
    for suggestion in existing:
        other = suggestion.target_note_id if suggestion.source_note_id == note.id else suggestion.source_note_id
        current = (
            versions.get(suggestion.source_note_id) == suggestion.source_updated_at
            and versions.get(suggestion.target_note_id) == suggestion.target_updated_at
        )
        if suggestion.status == "rejected" and current:
            desired.pop(other, None)  # the user already said no to exactly these note versions
            suppressed += 1
        elif other not in desired:
            removable.append(suggestion.id)

    if removable:  # these rows are locked FOR UPDATE above, so no user action can race this delete
        db.execute(delete(Suggestion).where(Suggestion.id.in_(removable)))

    for candidate in desired.values():
        source_id, target_id = canonical_pair(note.id, candidate.note_id)
        note_is_source = source_id == note.id
        values = {
            "owner_id": owner_id,
            "source_note_id": source_id,
            "target_note_id": target_id,
            "similarity_score": candidate.score,
            "explanation": candidate.explanation,
            "status": "pending",
            "source_updated_at": note.updated_at if note_is_source else candidate.updated_at,
            "target_updated_at": candidate.updated_at if note_is_source else note.updated_at,
            "rejected_at": None,
            "created_at": utcnow(),
        }
        insert = pg_insert(Suggestion).values(**values)
        excluded = insert.excluded
        db.execute(
            insert.on_conflict_do_update(
                index_elements=["source_note_id", "target_note_id"],
                set_={
                    k: getattr(excluded, k)
                    for k in (
                        "similarity_score",
                        "explanation",
                        "status",
                        "source_updated_at",
                        "target_updated_at",
                        "rejected_at",
                    )
                },
                # Never resurrect a rejection that still applies to these exact note versions.
                where=(
                    (Suggestion.status != "rejected")
                    | (Suggestion.source_updated_at != excluded.source_updated_at)
                    | (Suggestion.target_updated_at != excluded.target_updated_at)
                ),
            )
        )
    return RefreshResult(upserted=len(desired), removed=len(removable), suppressed=suppressed)


def make_event_handler(session_factory: Callable[[], Session], settings: Settings | None = None):
    def handle(event: NoteEvent) -> None:
        if event.event_type is NoteEventType.DELETED:
            return  # foreign keys already removed the note's suggestions and links
        with session_factory() as db:
            result = refresh_suggestions(db, event.note_id, event.owner_id, settings or get_settings())
            db.commit()
        logger.info(
            "suggestions refreshed",
            extra={
                "event_id": str(event.event_id),
                "note_id": str(event.note_id),
                "skipped": result.skipped,
                "upserted": result.upserted,
                "removed": result.removed,
                "suppressed": result.suppressed,
            },
        )

    return handle
