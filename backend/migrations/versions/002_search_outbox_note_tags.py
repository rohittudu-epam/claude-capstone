"""Weighted search vector, outbox without note FK, composite note_tags key.

Revision ID: 002
Revises: 001
Create Date: 2026-10-17
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

SEARCH_VECTOR_SQL = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(body, '')), 'B')"
)


def upgrade() -> None:
    # Title-weighted full-text search (FR-7: title matches rank above body-only matches).
    op.execute("DROP INDEX IF EXISTS ix_notes_body_gin")
    op.execute(f"ALTER TABLE notes ADD COLUMN search_vector tsvector GENERATED ALWAYS AS ({SEARCH_VECTOR_SQL}) STORED")
    op.execute("CREATE INDEX ix_notes_search_vector ON notes USING GIN (search_vector)")

    # 'deleted' events must outlive the note row, so the outbox cannot cascade from notes.
    op.drop_constraint("outbox_note_id_fkey", "outbox", type_="foreignkey")
    op.create_index("ix_outbox_note_id", "outbox", ["note_id"])

    # note_tags becomes a plain association table keyed by (note_id, tag_id).
    op.execute("ALTER TABLE note_tags DROP CONSTRAINT uq_note_tags_note_id_tag_id")
    op.execute("ALTER TABLE note_tags DROP CONSTRAINT note_tags_pkey")
    op.execute("ALTER TABLE note_tags DROP COLUMN id")
    op.execute("ALTER TABLE note_tags ADD PRIMARY KEY (note_id, tag_id)")

    # Remove redundant structures from 001 (the composite PK covers note_id lookups; unique indexes
    # already enforce email and jti uniqueness) and add the missing suggestions index.
    op.execute("DROP INDEX IF EXISTS ix_note_tags_note_id")
    op.execute("DROP INDEX IF EXISTS ix_notes_title")
    op.execute("ALTER TABLE users DROP CONSTRAINT users_email_key")
    op.execute("ALTER TABLE revoked_tokens DROP CONSTRAINT revoked_tokens_token_jti_key")
    op.execute("CREATE INDEX ix_suggestions_target_note_id ON suggestions (target_note_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_suggestions_target_note_id")
    op.execute("ALTER TABLE revoked_tokens ADD CONSTRAINT revoked_tokens_token_jti_key UNIQUE (token_jti)")
    op.execute("ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email)")
    op.execute("CREATE INDEX ix_notes_title ON notes (title)")
    op.execute("CREATE INDEX ix_note_tags_note_id ON note_tags (note_id)")

    op.execute("ALTER TABLE note_tags DROP CONSTRAINT note_tags_pkey")
    op.execute("ALTER TABLE note_tags ADD COLUMN id uuid NOT NULL DEFAULT gen_random_uuid()")
    op.execute("ALTER TABLE note_tags ADD PRIMARY KEY (id)")
    op.execute("ALTER TABLE note_tags ADD CONSTRAINT uq_note_tags_note_id_tag_id UNIQUE (note_id, tag_id)")

    op.drop_index("ix_outbox_note_id", table_name="outbox")
    op.execute("DELETE FROM outbox WHERE note_id NOT IN (SELECT id FROM notes)")
    op.create_foreign_key("outbox_note_id_fkey", "outbox", "notes", ["note_id"], ["id"], ondelete="CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_notes_search_vector")
    op.execute("ALTER TABLE notes DROP COLUMN search_vector")
    op.execute("CREATE INDEX ix_notes_body_gin ON notes USING GIN (to_tsvector('english', body))")
