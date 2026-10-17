from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AfterValidator, BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from shared.auth import get_current_user_id
from shared.config import get_settings
from shared.db import get_db
from shared.models import AcceptedLink, Note
from shared.tags import note_ids_with_all_tags, parse_tag_filter
from shared.timeutil import as_utc

router = APIRouter(prefix="/api/graph", tags=["graph"])

UTCDatetime = Annotated[datetime, AfterValidator(as_utc)]


class GraphNode(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    tags: list[str]
    created_at: UTCDatetime
    updated_at: UTCDatetime


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    created_at: UTCDatetime


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_nodes: int
    max_nodes: int
    is_capped: bool
    message: str | None


@router.get("", response_model=GraphResponse)
def get_graph(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_db)],
    tags: Annotated[list[str], Query()] = [],  # noqa: B006 (FastAPI copies the default)
) -> GraphResponse:
    """The caller's notes (optionally only those carrying every tag in `tags`) and the accepted links between them.

    At most `graph_max_nodes` notes are returned, most recently updated first. `total_nodes` counts every
    matching note, and an edge appears only when both of its notes are in the response.
    """
    try:
        tag_names = parse_tag_filter(tags)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid tags filter: {exc}") from None

    limit = get_settings().graph_max_nodes
    matching = select(Note).where(Note.owner_id == user_id)
    if tag_names:
        matching = matching.where(Note.id.in_(note_ids_with_all_tags(user_id, tag_names)))
    total = db.scalar(select(func.count()).select_from(matching.subquery())) or 0
    notes = db.scalars(
        matching.order_by(Note.updated_at.desc(), Note.id).limit(limit).options(selectinload(Note.tags))
    ).all()

    node_ids = [n.id for n in notes]
    links = (
        db.scalars(
            select(AcceptedLink)
            .where(
                AcceptedLink.owner_id == user_id,
                AcceptedLink.source_note_id.in_(node_ids),
                AcceptedLink.target_note_id.in_(node_ids),
            )
            .order_by(AcceptedLink.created_at, AcceptedLink.id)
        ).all()
        if node_ids
        else []
    )

    capped = total > limit
    return GraphResponse(
        nodes=[
            GraphNode(
                id=n.id,
                owner_id=n.owner_id,
                title=n.title,
                tags=[t.name for t in n.tags],
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in notes
        ],
        edges=[
            GraphEdge(id=link.id, source=link.source_note_id, target=link.target_note_id, created_at=link.created_at)
            for link in links
        ],
        total_nodes=total,
        max_nodes=limit,
        is_capped=capped,
        message=(
            f"Showing the {limit} most recently updated of {total} matching notes. Add tag filters to narrow the graph."
            if capped
            else None
        ),
    )
