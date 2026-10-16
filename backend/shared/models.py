"""Shared SQLAlchemy models for LinkNote MVP."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    UUID,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User domain entity."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="owner", cascade="all, delete-orphan")
    revoked_tokens = relationship("RevokedToken", back_populates="user", cascade="all, delete-orphan")


class Note(Base):
    """Note domain entity."""

    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary="note_tags", back_populates="notes")
    note_tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")
    outbox_entries = relationship("OutboxEntry", back_populates="note", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_notes_owner_id_updated_at", "owner_id", "updated_at"),
        Index(
            "ix_notes_body_gin",
            func.to_tsvector("english", body),
            postgresql_using="gin",
        ),
    )


class Tag(Base):
    """Tag domain entity."""

    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    owner = relationship("User", back_populates="tags")
    notes = relationship("Note", secondary="note_tags", back_populates="tags")

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_tags_owner_id_name"),)


class NoteTag(Base):
    """Association between notes and tags."""

    __tablename__ = "note_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)

    note = relationship("Note", back_populates="note_tags")
    tag = relationship("Tag")

    __table_args__ = (UniqueConstraint("note_id", "tag_id", name="uq_note_tags_note_id_tag_id"),)


class AcceptedLink(Base):
    """Accepted bidirectional link between notes."""

    __tablename__ = "accepted_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_note_id", "target_note_id", name="uq_accepted_links_pair"),
        CheckConstraint("source_note_id < target_note_id", name="ck_accepted_links_canonical_order"),
    )


class Suggestion(Base):
    """Pending link suggestion for user review."""

    __tablename__ = "suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("source_note_id", "target_note_id", name="uq_suggestions_pair"),
        Index("ix_suggestions_owner_id_created_at", "owner_id", "created_at"),
    )


class OutboxEntry(Base):
    """Transactional Outbox for reliable event publishing."""

    __tablename__ = "outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)
    schema_version = Column(String(10), nullable=False, default="1")
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    note = relationship("Note", back_populates="outbox_entries")

    __table_args__ = (Index("ix_outbox_published_at_created_at", "published_at", "created_at"),)


class RevokedToken(Base):
    """Revoked JWT tokens."""

    __tablename__ = "revoked_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(255), nullable=False, unique=True, index=True)
    revoked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="revoked_tokens")

    __table_args__ = (Index("ix_revoked_tokens_expires_at", "expires_at"),)
