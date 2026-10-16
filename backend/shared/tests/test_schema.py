"""Schema, constraint, and migration behaviour against a real PostgreSQL."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import func, select, text

from conftest import alembic_config
from shared.models import AcceptedLink, Base, Note, NoteTag, OutboxEntry, RevokedToken, Suggestion, Tag, User
from shared.timeutil import utcnow


@pytest.fixture
def owner(session_factory):
    with session_factory() as db:
        user = User(email="owner@example.com", password_hash="x")
        db.add(user)
        db.commit()
    return user


@pytest.fixture
def two_notes(session_factory, owner):
    with session_factory() as db:
        notes = [Note(owner_id=owner.id, title=t, body="b") for t in ("one", "two")]
        db.add_all(notes)
        db.commit()
    return sorted(notes, key=lambda n: n.id)


def run(engine, sql: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(sql))


def assert_rejected(engine, insert_sql: str) -> None:
    """Runs the INSERT inside a DO block that swallows integrity violations server-side.

    The local test database (PGlite) cannot survive a client-visible SQL error, and the block also
    proves the statement was rejected for an integrity reason rather than, say, a typo. If the insert
    is wrongly accepted the block raises and the test fails.
    """
    run(
        engine,
        f"""DO $$ BEGIN
              {insert_sql};
              RAISE EXCEPTION 'insert was accepted but should have violated a constraint';
            EXCEPTION WHEN integrity_constraint_violation THEN NULL;
            END $$""",
    )


def user_sql(email, user_id=None):
    return f"INSERT INTO users (id,email,password_hash,created_at,updated_at) VALUES ('{user_id or uuid4()}','{email}','h',now(),now())"


def tag_sql(owner_id, name):
    return f"INSERT INTO tags (id,owner_id,name,created_at) VALUES ('{uuid4()}','{owner_id}','{name}',now())"


def note_sql(owner_id):
    return f"INSERT INTO notes (id,owner_id,title,body,created_at,updated_at) VALUES ('{uuid4()}','{owner_id}','t','b',now(),now())"


def link_sql(owner, source, target):
    return (
        "INSERT INTO accepted_links (id,source_note_id,target_note_id,owner_id,created_at) "
        f"VALUES ('{uuid4()}','{source.id}','{target.id}','{owner.id}',now())"
    )


def suggestion_sql(owner, source, target):
    return (
        "INSERT INTO suggestions (id,source_note_id,target_note_id,owner_id,similarity_score,explanation,created_at) "
        f"VALUES ('{uuid4()}','{source.id}','{target.id}','{owner.id}',0.4,'e',now())"
    )


def revoked_sql(owner, jti):
    return (
        "INSERT INTO revoked_tokens (id,user_id,token_jti,revoked_at,expires_at) "
        f"VALUES ('{uuid4()}','{owner.id}','{jti}',now(),now())"
    )


class TestConstraints:
    def test_email_must_be_unique(self, engine, owner):
        assert_rejected(engine, user_sql("owner@example.com"))

    def test_tag_names_are_unique_per_owner_only(self, engine, owner):
        other = uuid4()
        run(engine, user_sql("other@example.com", other))
        run(engine, tag_sql(owner.id, "t"))
        run(engine, tag_sql(other, "t"))
        assert_rejected(engine, tag_sql(owner.id, "t"))

    def test_note_requires_an_existing_owner(self, engine, session_factory):
        assert_rejected(engine, note_sql(uuid4()))

    def test_accepted_link_cannot_be_duplicated_or_stored_in_reverse_order(self, engine, owner, two_notes):
        low, high = two_notes
        run(engine, link_sql(owner, low, high))
        assert_rejected(engine, link_sql(owner, low, high))
        assert_rejected(engine, link_sql(owner, high, low))  # the same logical pair

    def test_a_note_cannot_link_to_itself(self, engine, owner, two_notes):
        assert_rejected(engine, link_sql(owner, two_notes[0], two_notes[0]))

    def test_one_pending_suggestion_per_ordered_pair(self, engine, owner, two_notes):
        low, high = two_notes
        run(engine, suggestion_sql(owner, low, high))
        assert_rejected(engine, suggestion_sql(owner, low, high))

    def test_revoked_token_jti_is_unique(self, engine, owner):
        run(engine, revoked_sql(owner, "abc"))
        assert_rejected(engine, revoked_sql(owner, "abc"))


class TestCascades:
    def test_deleting_a_note_removes_its_links_suggestions_and_tag_associations(
        self, session_factory, owner, two_notes
    ):
        low, high = two_notes
        with session_factory() as db:
            tag = Tag(owner_id=owner.id, name="t")
            db.add(tag)
            db.flush()
            db.add_all(
                [
                    NoteTag(note_id=low.id, tag_id=tag.id),
                    AcceptedLink(source_note_id=low.id, target_note_id=high.id, owner_id=owner.id),
                    Suggestion(
                        source_note_id=high.id,
                        target_note_id=low.id,
                        owner_id=owner.id,
                        similarity_score=1,
                        explanation="e",
                    ),
                ]
            )
            db.commit()
        with session_factory() as db:
            db.execute(text("DELETE FROM notes WHERE id = :id"), {"id": low.id})
            db.commit()
        with session_factory() as db:
            models = (AcceptedLink, Suggestion, NoteTag, Tag, Note)
            counts = [db.scalar(select(func.count()).select_from(m)) for m in models]
        assert counts == [0, 0, 0, 1, 1]  # the tag itself survives; only the associations go

    def test_deleting_a_user_removes_everything_they_own(self, session_factory, owner, two_notes):
        with session_factory() as db:
            db.add_all(
                [
                    Tag(owner_id=owner.id, name="t"),
                    RevokedToken(user_id=owner.id, token_jti="j", expires_at=utcnow()),
                    OutboxEntry(note_id=uuid4(), owner_id=owner.id, event_type="created", payload="{}"),
                ]
            )
            db.commit()
        with session_factory() as db:
            db.execute(text("DELETE FROM users"))
            db.commit()
        with session_factory() as db:
            for model in (Note, Tag, RevokedToken, OutboxEntry):
                assert db.scalar(select(func.count()).select_from(model)) == 0


class TestSearchVector:
    def test_is_generated_from_title_and_body_with_title_weighted_higher(self, session_factory, owner):
        with session_factory() as db:
            db.add(Note(owner_id=owner.id, title="Kubernetes", body="pods"))
            db.commit()
            vector = db.execute(text("SELECT search_vector::text FROM notes")).scalar_one()
        assert "'kubernet':1A" in vector and "'pod':2B" in vector


class TestMigrations:
    @pytest.fixture
    def sandbox(self, engine):
        def reset() -> None:
            with engine.begin() as conn:
                conn.execute(text("DROP SCHEMA public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))

        reset()
        yield alembic_config()
        reset()
        command.upgrade(alembic_config(), "head")

    def test_fresh_database_upgrades_and_fully_downgrades(self, sandbox, engine):
        command.upgrade(sandbox, "head")
        command.downgrade(sandbox, "base")
        with engine.connect() as conn:
            tables = (
                conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
                )
                .scalars()
                .all()
            )
        assert tables == []
        command.upgrade(sandbox, "head")

    def test_existing_database_with_data_upgrades_without_losing_rows(self, sandbox, engine):
        command.upgrade(sandbox, "001")
        user, note, tag = uuid4(), uuid4(), uuid4()
        statements = [
            (
                "INSERT INTO users (id,email,password_hash,created_at,updated_at) VALUES (:u,'a@b.c','h',now(),now())",
                {},
            ),
            (
                "INSERT INTO notes (id,owner_id,title,body,created_at,updated_at) VALUES (:n,:u,'Kubernetes','pods',now(),now())",
                {},
            ),
            ("INSERT INTO tags (id,owner_id,name,created_at) VALUES (:t,:u,'ops',now())", {}),
            ("INSERT INTO note_tags (id,note_id,tag_id) VALUES (:i,:n,:t)", {"i": uuid4()}),
            (
                "INSERT INTO outbox (id,note_id,owner_id,event_type,payload,schema_version,created_at) VALUES (:i,:n,:u,'created','{}','1',now())",
                {"i": uuid4()},
            ),
        ]
        with engine.begin() as conn:
            for sql, extra in statements:
                conn.execute(text(sql), {"u": user, "n": note, "t": tag, **extra})

        command.upgrade(sandbox, "head")

        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM note_tags")).scalar_one() == 1
            assert conn.execute(text("SELECT count(*) FROM outbox")).scalar_one() == 1
            matching = "SELECT count(*) FROM notes WHERE search_vector @@ to_tsquery('english','kubernetes')"
            assert conn.execute(text(matching)).scalar_one() == 1

    def test_models_and_migrations_have_not_drifted(self, engine):
        with engine.connect() as conn:
            diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diffs == []
