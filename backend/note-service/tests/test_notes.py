import time
from datetime import timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from note_service.main import app
from shared.config import get_settings
from shared.models import AcceptedLink, Note, NoteTag, OutboxEntry, RevokedToken, Suggestion, Tag
from shared.security import ACCESS
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


def create(client, user, title="Kubernetes notes", body="# Pods\nand deployments", tags=None):
    payload = {"title": title, "body": body}
    if tags is not None:
        payload["tags"] = tags
    response = client.post("/api/notes", json=payload, headers=user.headers)
    assert response.status_code == 201, response.text
    return response.json()


class TestAuthentication:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("POST", "/api/notes"),
            ("GET", "/api/notes"),
            ("GET", "/api/notes/search?q=x"),
            ("GET", f"/api/notes/{uuid4()}"),
            ("PUT", f"/api/notes/{uuid4()}"),
            ("DELETE", f"/api/notes/{uuid4()}"),
            ("GET", "/api/tags"),
        ],
    )
    def test_requires_authentication(self, client, method, path):
        response = client.request(method, path, json={"title": "t", "body": "b"} if method in ("POST", "PUT") else None)
        assert response.status_code == 401

    def test_rejects_revoked_token(self, client, alice, session_factory):
        assert client.get("/api/notes", headers=alice.headers).status_code == 200
        with session_factory() as db:
            db.add(RevokedToken(user_id=alice.id, token_jti=alice.jti, expires_at=func.now() + timedelta(hours=1)))
            db.commit()
        assert client.get("/api/notes", headers=alice.headers).status_code == 401

    def test_rejects_expired_and_forged_tokens(self, client, alice):
        claims = {"sub": str(alice.id), "jti": uuid4().hex, "type": ACCESS, "iat": int(time.time()) - 100}
        expired = jwt.encode({**claims, "exp": int(time.time()) - 10}, get_settings().jwt_secret_key, algorithm="HS256")
        forged = jwt.encode({**claims, "exp": int(time.time()) + 600}, "x" * 40, algorithm="HS256")
        for token in (expired, forged):
            assert client.get("/api/notes", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    def test_accepts_access_token_cookie(self, client, alice):
        client.cookies.set("access_token", alice.token)
        assert client.get("/api/notes").status_code == 200


class TestCrud:
    def test_create_and_retrieve(self, client, alice):
        created = create(client, alice, tags=["DevOps"])
        assert created["owner_id"] == str(alice.id)
        assert created["tags"] == ["devops"]
        assert created["created_at"] == created["updated_at"]
        fetched = client.get(f"/api/notes/{created['id']}", headers=alice.headers)
        assert fetched.status_code == 200
        assert fetched.json() == created

    @pytest.mark.parametrize(
        "payload",
        [
            {"body": "no title"},
            {"title": "no body"},
            {"title": "", "body": "x"},
            {"title": "   ", "body": "x"},
            {"title": "t" * 501, "body": "x"},
            {"title": "t", "body": "x", "tags": ["  "]},
            {"title": "t", "body": "x", "tags": ["a" * 51]},
            {"title": "t", "body": "x", "tags": [f"tag{i}" for i in range(21)]},
            {"title": "t", "body": "x", "owner_id": str(uuid4())},
        ],
    )
    def test_invalid_payload_returns_400(self, client, alice, payload):
        response = client.post("/api/notes", json=payload, headers=alice.headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid request"

    def test_oversized_body_rejected(self, client, alice):
        body = "x" * (get_settings().note_max_body_bytes + 1)
        assert client.post("/api/notes", json={"title": "t", "body": body}, headers=alice.headers).status_code == 400

    def test_malformed_id_returns_400(self, client, alice):
        assert client.get("/api/notes/not-a-uuid", headers=alice.headers).status_code == 400

    def test_update_changes_content_and_timestamp(self, client, alice):
        created = create(client, alice)
        response = client.put(
            f"/api/notes/{created['id']}", json={"title": "New title", "body": "New body"}, headers=alice.headers
        )
        assert response.status_code == 200
        updated = response.json()
        assert (updated["title"], updated["body"]) == ("New title", "New body")
        assert updated["created_at"] == created["created_at"]
        assert updated["updated_at"] > created["updated_at"]

    def test_update_without_changes_keeps_timestamp(self, client, alice):
        created = create(client, alice)
        response = client.put(
            f"/api/notes/{created['id']}",
            json={"title": created["title"], "body": created["body"]},
            headers=alice.headers,
        )
        assert response.json()["updated_at"] == created["updated_at"]

    def test_delete(self, client, alice):
        created = create(client, alice)
        assert client.delete(f"/api/notes/{created['id']}", headers=alice.headers).status_code == 204
        assert client.get(f"/api/notes/{created['id']}", headers=alice.headers).status_code == 404
        assert client.delete(f"/api/notes/{created['id']}", headers=alice.headers).status_code == 404

    def test_delete_cascades_to_tags_links_and_suggestions(self, client, alice, session_factory):
        first = create(client, alice, title="First", tags=["a"])
        second = create(client, alice, title="Second")
        low, high = sorted([first["id"], second["id"]])
        with session_factory() as db:
            db.add(AcceptedLink(source_note_id=low, target_note_id=high, owner_id=alice.id))
            db.add(
                Suggestion(
                    source_note_id=low,
                    target_note_id=high,
                    owner_id=alice.id,
                    similarity_score=0.5,
                    explanation="shared: x",
                    source_updated_at=utcnow(),
                    target_updated_at=utcnow(),
                )
            )
            db.commit()
        client.delete(f"/api/notes/{first['id']}", headers=alice.headers)
        with session_factory() as db:
            assert db.scalar(select(func.count()).select_from(AcceptedLink)) == 0
            assert db.scalar(select(func.count()).select_from(Suggestion)) == 0
            assert db.scalar(select(func.count()).select_from(NoteTag)) == 0
            assert db.scalar(select(func.count()).select_from(Note)) == 1

    def test_pagination_orders_by_most_recently_updated_and_hides_bodies(self, client, alice):
        ids = [create(client, alice, title=f"Note {i}")["id"] for i in range(5)]
        page = client.get("/api/notes", params={"limit": 2, "offset": 1}, headers=alice.headers).json()
        assert page["total"] == 5 and page["limit"] == 2 and page["offset"] == 1
        assert [item["id"] for item in page["items"]] == [ids[3], ids[2]]
        assert all("body" not in item for item in page["items"])

    @pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
    def test_invalid_pagination_returns_400(self, client, alice, params):
        assert client.get("/api/notes", params=params, headers=alice.headers).status_code == 400


class TestOwnership:
    def test_other_users_notes_are_invisible_and_immutable(self, client, alice, bob):
        note = create(client, alice, title="Private")
        url = f"/api/notes/{note['id']}"
        assert client.get(url, headers=bob.headers).status_code == 404
        assert client.put(url, json={"title": "Hacked", "body": "x"}, headers=bob.headers).status_code == 404
        assert client.delete(url, headers=bob.headers).status_code == 404
        assert client.get("/api/notes", headers=bob.headers).json()["total"] == 0
        assert client.get(url, headers=alice.headers).json()["title"] == "Private"


class TestTags:
    def test_reuses_normalised_tags_without_duplicates(self, client, alice, session_factory):
        create(client, alice, title="One", tags=["DevOps", "  devops ", "Dev   Ops"])
        create(client, alice, title="Two", tags=["DEVOPS"])
        with session_factory() as db:
            names = sorted(db.scalars(select(Tag.name)))
        assert names == ["dev ops", "devops"]

    def test_tags_are_scoped_per_user(self, client, alice, bob, session_factory):
        create(client, alice, tags=["shared-name"])
        create(client, bob, tags=["shared-name"])
        with session_factory() as db:
            assert db.scalar(select(func.count()).select_from(Tag)) == 2
        assert [t["name"] for t in client.get("/api/tags", headers=alice.headers).json()] == ["shared-name"]

    def test_filter_uses_and_semantics(self, client, alice):
        both = create(client, alice, title="Both", tags=["devops", "backend"])
        create(client, alice, title="Only devops", tags=["devops"])
        create(client, alice, title="Untagged")
        for query in ({"tags": "devops,backend"}, {"tags": ["devops", "backend"]}, {"tags": "DevOps , BACKEND"}):
            page = client.get("/api/notes", params=query, headers=alice.headers).json()
            assert [i["id"] for i in page["items"]] == [both["id"]], query
            assert page["total"] == 1
        assert client.get("/api/notes", params={"tags": "devops"}, headers=alice.headers).json()["total"] == 2

    def test_filter_with_unknown_tag_returns_nothing(self, client, alice):
        create(client, alice, tags=["devops"])
        page = client.get("/api/notes", params={"tags": "devops,nope"}, headers=alice.headers).json()
        assert page["items"] == [] and page["total"] == 0

    def test_filter_cannot_see_other_users_tagged_notes(self, client, alice, bob):
        create(client, alice, tags=["secret"])
        page = client.get("/api/notes", params={"tags": "secret"}, headers=bob.headers).json()
        assert page["total"] == 0

    def test_update_replaces_keeps_or_clears_tags_without_deleting_the_note(self, client, alice):
        note = create(client, alice, tags=["a", "b"])
        url = f"/api/notes/{note['id']}"
        body = {"title": note["title"], "body": note["body"]}

        kept = client.put(url, json=body, headers=alice.headers).json()
        assert kept["tags"] == ["a", "b"]
        replaced = client.put(url, json={**body, "tags": ["b", "c"]}, headers=alice.headers).json()
        assert replaced["tags"] == ["b", "c"]
        assert replaced["updated_at"] > note["updated_at"]
        cleared = client.put(url, json={**body, "tags": []}, headers=alice.headers)
        assert cleared.status_code == 200 and cleared.json()["tags"] == []
        assert client.get(url, headers=alice.headers).status_code == 200

    def test_list_tags_with_counts(self, client, alice):
        create(client, alice, title="1", tags=["x", "y"])
        create(client, alice, title="2", tags=["x"])
        tags = client.get("/api/tags", headers=alice.headers).json()
        assert [(t["name"], t["note_count"]) for t in tags] == [("x", 2), ("y", 1)]


class TestEvents:
    def outbox(self, session_factory):
        with session_factory() as db:
            return list(db.scalars(select(OutboxEntry).order_by(OutboxEntry.created_at)))

    def test_create_update_delete_emit_events_in_the_same_transaction(self, client, alice, session_factory):
        note = create(client, alice, title="Secret title", body="secret body text")
        url = f"/api/notes/{note['id']}"
        updated = client.put(url, json={"title": "Secret title", "body": "changed"}, headers=alice.headers).json()
        client.delete(url, headers=alice.headers)

        entries = self.outbox(session_factory)
        assert [e.event_type for e in entries] == ["created", "updated", "deleted"]
        assert all(str(e.note_id) == note["id"] and e.owner_id == alice.id for e in entries)
        assert all(e.published_at is None for e in entries)
        assert entries[0].payload.count(note["id"]) == 1
        assert f'"occurred_at":"{note["updated_at"][:19]}' in entries[0].payload
        assert f'"occurred_at":"{updated["updated_at"][:19]}' in entries[1].payload
        for entry in entries:
            assert "secret" not in entry.payload.lower() and "changed" not in entry.payload
            assert f'"event_id":"{entry.id}"' in entry.payload and '"schema_version":1' in entry.payload

    def test_deleted_event_survives_note_deletion(self, client, alice, session_factory):
        note = create(client, alice)
        client.delete(f"/api/notes/{note['id']}", headers=alice.headers)
        assert [e.event_type for e in self.outbox(session_factory)] == ["created", "deleted"]

    def test_no_event_for_rejected_or_unchanged_requests(self, client, alice, bob, session_factory):
        note = create(client, alice)
        before = len(self.outbox(session_factory))
        client.post("/api/notes", json={"title": "", "body": "x"}, headers=alice.headers)
        client.put(f"/api/notes/{note['id']}", json={"title": "x", "body": "y"}, headers=bob.headers)
        client.delete(f"/api/notes/{note['id']}", headers=bob.headers)
        client.put(
            f"/api/notes/{note['id']}",
            json={"title": note["title"], "body": note["body"], "tags": ["new"]},
            headers=alice.headers,
        )
        assert len(self.outbox(session_factory)) == before


class TestHealth:
    def test_health_is_up_and_ready_reports_each_dependency(self, client, monkeypatch):
        class Down:
            def ping(self):
                raise ConnectionError("redis down")

        monkeypatch.setattr("shared.health.create_redis", lambda: Down())
        assert client.get("/health").status_code == 200
        ready = client.get("/ready")
        assert ready.status_code == 503
        assert ready.json()["checks"] == {"database": "ok", "redis": "unavailable"}
