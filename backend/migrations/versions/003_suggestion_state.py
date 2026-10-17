"""Suggestion status, note versions, and one-row-per-pair ordering.

Revision ID: 003
Revises: 002
Create Date: 2026-10-17
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Suggestions are derived data. Put existing rows in canonical order where that is possible without
    # creating a duplicate, and drop the rest; the link worker regenerates them from the notes.
    op.execute(
        """
        UPDATE suggestions s
           SET source_note_id = s.target_note_id, target_note_id = s.source_note_id
         WHERE s.source_note_id > s.target_note_id
           AND NOT EXISTS (
                 SELECT 1 FROM suggestions r
                  WHERE r.source_note_id = s.target_note_id AND r.target_note_id = s.source_note_id)
        """
    )
    op.execute("DELETE FROM suggestions WHERE source_note_id >= target_note_id")

    op.execute("ALTER TABLE suggestions ADD COLUMN status varchar(20) NOT NULL DEFAULT 'pending'")
    op.execute("ALTER TABLE suggestions ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE suggestions ADD COLUMN rejected_at timestamp")
    for column, note_column in (("source_updated_at", "source_note_id"), ("target_updated_at", "target_note_id")):
        op.execute(f"ALTER TABLE suggestions ADD COLUMN {column} timestamp")
        op.execute(f"UPDATE suggestions s SET {column} = n.updated_at FROM notes n WHERE n.id = s.{note_column}")
        op.execute(f"ALTER TABLE suggestions ALTER COLUMN {column} SET NOT NULL")

    op.execute(
        "ALTER TABLE suggestions ADD CONSTRAINT ck_suggestions_canonical_order CHECK (source_note_id < target_note_id)"
    )
    op.execute("ALTER TABLE suggestions ADD CONSTRAINT ck_suggestions_status CHECK (status IN ('pending', 'rejected'))")


def downgrade() -> None:
    op.execute("ALTER TABLE suggestions DROP CONSTRAINT ck_suggestions_status")
    op.execute("ALTER TABLE suggestions DROP CONSTRAINT ck_suggestions_canonical_order")
    for column in ("target_updated_at", "source_updated_at", "rejected_at", "status"):
        op.execute(f"ALTER TABLE suggestions DROP COLUMN {column}")
