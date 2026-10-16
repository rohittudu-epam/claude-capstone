"""Shared SQLAlchemy models for LinkNote MVP."""

from datetime import datetime
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from shared.timeutil import utcnow

SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(body, '')), 'B')"
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(SEARCH_VECTOR_SQL, persisted=True), deferred=True
    )

    tags: Mapped[list[Tag]] = relationship(secondary="note_tags", back_populates="notes", order_by="Tag.name")

    __table_args__ = (
        Index("ix_notes_owner_id_updated_at", "owner_id", "updated_at"),
        Index("ix_notes_search_vector", "search_vector", postgresql_using="gin"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    notes: Mapped[list[Note]] = relationship(secondary="note_tags", back_populates="tags")

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_tags_owner_id_name"),)


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id: Mapped[PyUUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[PyUUID] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True)


class AcceptedLink(Base):
    """Accepted link; stored once per pair with source_note_id < target_note_id."""

    __tablename__ = "accepted_links"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    source_note_id: Mapped[PyUUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    target_note_id: Mapped[PyUUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("source_note_id", "target_note_id", name="uq_accepted_links_pair"),
        CheckConstraint("source_note_id < target_note_id", name="ck_accepted_links_canonical_order"),
    )


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    source_note_id: Mapped[PyUUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    target_note_id: Mapped[PyUUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    owner_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    similarity_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("source_note_id", "target_note_id", name="uq_suggestions_pair"),
        Index("ix_suggestions_owner_id_created_at", "owner_id", "created_at"),
    )


class OutboxEntry(Base):
    """Transactional outbox. note_id is intentionally not a foreign key so
    'deleted' events survive the deletion of the note they describe."""

    __tablename__ = "outbox"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    note_id: Mapped[PyUUID] = mapped_column(index=True)
    owner_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[str] = mapped_column(Text)
    schema_version: Mapped[str] = mapped_column(String(10), default="1")
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (Index("ix_outbox_published_at_created_at", "published_at", "created_at"),)


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_jti: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    revoked_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
