import random
import time
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.exc import OperationalError

from graph_service.main import app
from shared.config import get_settings
from shared.db import get_db
from shared.links import canonical_pair
from shared.models import AcceptedLink, Note, NoteTag, Tag
from shared.timeutil import utcnow


@pytest.fixture
def client(session_factory) -> TestClient:
    return TestClient(app)


@pytest.fixture
def alice(make_user):
    return make_user("alice@example.com")


@pytest.fixture
def bob(make_user):
    return make_user("bob@example.com")


@pytest.fixture
def build(session_factory):
    """Creates notes (optionally tagged) and links between them directly in the database."""

    def notes(owner, count, *, tags=None, start=0):
        base = utcnow()
        tag_ids = {}
        created = []
        with session_factory() as db:
            for name in {t for tag_list in (tags or []) for t in tag_list}:
                tag = Tag(owner_id=owner.id, name=name)
                db.add(tag)
                db.flush()
                tag_ids[name] = tag.id
            for i in range(count):
                stamp = base + timedelta(seconds=start + i)
                note = Note(owner_id=owner.id, title=f"Note {start + i}", body="b", created_at=stamp, updated_at=stamp)
                db.add(note)
                db.flush()
                for name in tags[i] if tags else []:
                    db.add(NoteTag(note_id=note.id, tag_id=tag_ids[name]))
                created.append(note)
            db.commit()
        return created

    def link(owner, a, b):
        low, high = canonical_pair(a.id, b.id)
        with session_factory() as db:
            db.add(AcceptedLink(source_note_id=low, target_note_id=high, owner_id=owner.id))
            db.commit()

    return notes, link


def get_graph(client, user, **params):
    return client.get("/api/graph", params=params, headers=user.headers)


def test_requires_authentication(client):
    assert client.get("/api/graph").status_code == 401


def test_empty_graph(client, alice):
    body = get_graph(client, alice).json()
    assert body == {
        "nodes": [],
        "edges": [],
        "total_nodes": 0,
        "max_nodes": 500,
        "is_capped": False,
        "message": None,
    }


class TestStructure:
    def test_nodes_and_edges_reference_each_other_consistently(self, client, alice, build):
        notes, link = build
        a, b, c = notes(alice, 3, tags=[["x"], ["x", "y"], []])
        link(alice, a, b)
        link(alice, c, b)
        body = get_graph(client, alice).json()

        by_id = {n["id"]: n for n in body["nodes"]}
        assert set(by_id) == {str(a.id), str(b.id), str(c.id)}
        assert by_id[str(b.id)]["tags"] == ["x", "y"] and by_id[str(b.id)]["owner_id"] == str(alice.id)
        assert body["total_nodes"] == 3 and body["is_capped"] is False
        assert len(body["edges"]) == 2
        for edge in body["edges"]:
            assert edge["source"] in by_id and edge["target"] in by_id and edge["source"] != edge["target"]
        assert {frozenset((e["source"], e["target"])) for e in body["edges"]} == {
            frozenset((str(a.id), str(b.id))),
            frozenset((str(b.id), str(c.id))),
        }

    def test_nodes_are_most_recently_updated_first(self, client, alice, build):
        notes, _ = build
        created = notes(alice, 3)
        titles = [n["title"] for n in get_graph(client, alice).json()["nodes"]]
        assert titles == [n.title for n in reversed(created)]


class TestIsolation:
    def test_never_includes_another_users_notes_or_links(self, client, alice, bob, build):
        notes, link = build
        a1, a2 = notes(alice, 2)
        link(alice, a1, a2)
        (b1,) = notes(bob, 1, start=10)
        body = get_graph(client, bob).json()
        assert [n["id"] for n in body["nodes"]] == [str(b1.id)] and body["edges"] == []
        assert body["total_nodes"] == 1


class TestTagFilter:
    def test_uses_and_semantics_and_drops_edges_to_hidden_notes(self, client, alice, build):
        notes, link = build
        both, only_x, also_both = notes(alice, 3, tags=[["x", "y"], ["x"], ["x", "y"]])
        link(alice, both, also_both)
        link(alice, both, only_x)  # only_x is filtered out, so this edge must disappear
        body = get_graph(client, alice, tags="x,y").json()
        assert {n["id"] for n in body["nodes"]} == {str(both.id), str(also_both.id)}
        assert [frozenset((e["source"], e["target"])) for e in body["edges"]] == [
            frozenset((str(both.id), str(also_both.id)))
        ]
        assert body["total_nodes"] == 2

    def test_accepts_repeated_and_unnormalised_tags(self, client, alice, build):
        notes, _ = build
        notes(alice, 2, tags=[["x", "y"], ["x"]])
        assert len(get_graph(client, alice, tags=["X", " y "]).json()["nodes"]) == 1

    def test_unknown_tag_gives_an_empty_graph(self, client, alice, build):
        notes, _ = build
        notes(alice, 2, tags=[["x"], ["x"]])
        body = get_graph(client, alice, tags="nope").json()
        assert body["nodes"] == [] and body["total_nodes"] == 0

    def test_another_users_tag_does_not_widen_the_result(self, client, alice, bob, build):
        notes, _ = build
        notes(alice, 1, tags=[["secret"]])
        assert get_graph(client, bob, tags="secret").json()["nodes"] == []

    def test_blank_filter_pieces_are_ignored(self, client, alice, build):
        notes, _ = build
        notes(alice, 1, tags=[["x"]])
        assert len(get_graph(client, alice, tags=" , ,x,   ").json()["nodes"]) == 1

    def test_an_overlong_tag_returns_400(self, client, alice):
        response = get_graph(client, alice, tags="a" * 51)
        assert response.status_code == 400 and "Invalid tags filter" in response.json()["detail"]


class TestCapping:
    def test_reports_the_cap_and_never_returns_dangling_edges(self, client, alice, build, monkeypatch):
        monkeypatch.setattr(get_settings(), "graph_max_nodes", 3)
        notes, link = build
        created = notes(alice, 5)
        for a, b in zip(created, created[1:], strict=False):  # a chain across the cap boundary
            link(alice, a, b)
        body = get_graph(client, alice).json()

        assert body["is_capped"] is True and body["total_nodes"] == 5 and body["max_nodes"] == 3
        assert "3 most recently updated of 5" in body["message"]
        assert [n["title"] for n in body["nodes"]] == ["Note 4", "Note 3", "Note 2"]
        ids = {n["id"] for n in body["nodes"]}
        assert len(body["edges"]) == 2
        assert all(e["source"] in ids and e["target"] in ids for e in body["edges"])

    def test_exactly_at_the_cap_is_not_capped(self, client, alice, build, monkeypatch):
        monkeypatch.setattr(get_settings(), "graph_max_nodes", 3)
        notes, _ = build
        notes(alice, 3)
        body = get_graph(client, alice).json()
        assert body["is_capped"] is False and body["message"] is None


class TestFailureModes:
    def test_database_outage_returns_a_documented_503_without_details(self, client, alice):
        def broken():
            raise OperationalError("SELECT 1", {}, Exception("connection to host db.internal password=hunter2 refused"))
            yield  # pragma: no cover

        app.dependency_overrides[get_db] = broken
        try:
            response = get_graph(client, alice)
        finally:
            app.dependency_overrides.clear()
        assert response.status_code == 503
        assert response.json()["detail"] == "Service temporarily unavailable"
        assert response.json()["correlation_id"] == response.headers["x-correlation-id"]
        assert "hunter2" not in response.text and "db.internal" not in response.text


def test_graph_of_a_1000_note_account_responds_within_one_second(client, alice, session_factory):
    rng = random.Random(3)
    now = utcnow()
    ids = [uuid4() for _ in range(1000)]
    with session_factory() as db:
        db.execute(
            insert(Note),
            [
                {
                    "id": i,
                    "owner_id": alice.id,
                    "title": f"Note {n}",
                    "body": "b",
                    "created_at": now,
                    "updated_at": now + timedelta(seconds=n),
                }
                for n, i in enumerate(ids)
            ],
        )
        pairs = {canonical_pair(*rng.sample(ids, 2)) for _ in range(2500)}
        db.execute(
            insert(AcceptedLink),
            [
                {"id": uuid4(), "source_note_id": a, "target_note_id": b, "owner_id": alice.id, "created_at": now}
                for a, b in pairs
            ],
        )
        db.commit()

    timings = []
    for _ in range(10):
        start = time.perf_counter()
        response = get_graph(client, alice)
        timings.append(time.perf_counter() - start)
        assert response.status_code == 200
    body = response.json()
    node_ids = {n["id"] for n in body["nodes"]}
    assert len(node_ids) == 500 and body["total_nodes"] == 1000 and body["is_capped"] is True
    assert body["edges"] and all(e["source"] in node_ids and e["target"] in node_ids for e in body["edges"])
    timings.sort()
    print(f"\ngraph p95 (1000 notes, {len(pairs)} links, 500 returned): {timings[-1] * 1000:.0f} ms")
    assert timings[-1] < 1.0
