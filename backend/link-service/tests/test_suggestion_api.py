from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from link_service.main import app
from shared.links import canonical_pair
from shared.models import AcceptedLink, Suggestion
from shared.timeutil import utcnow


@pytest.fixture
def client(session_factory) -> TestClient:
    return TestClient(app)


@pytest.fixture
def pending(alice, add_note, process, suggestions):
    """Two similar notes with one generated pending suggestion: (first, second, suggestion)."""
    first = add_note(alice, "Kubernetes deployment", "rolling updates pods services probes")
    second = add_note(alice, "Kubernetes deployments", "kubernetes rolling updates pods services")
    process(second, alice)
    (suggestion,) = suggestions()
    return first, second, suggestion


def link_count(session_factory) -> int:
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(AcceptedLink))


class TestAuthentication:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "/api/suggestions"),
            ("POST", f"/api/suggestions/{uuid4()}/accept"),
            ("POST", f"/api/suggestions/{uuid4()}/reject"),
            ("GET", "/api/links"),
        ],
    )
    def test_requires_authentication(self, client, method, path):
        assert client.request(method, path).status_code == 401


class TestListPending:
    def test_returns_context_needed_to_judge_a_suggestion(self, client, alice, pending):
        first, second, suggestion = pending
        page = client.get("/api/suggestions", headers=alice.headers).json()
        assert page["total"] == 1
        (item,) = page["items"]
        assert item["id"] == str(suggestion.id)
        assert {item["source_note"]["title"], item["target_note"]["title"]} == {first.title, second.title}
        assert {item["source_note"]["id"], item["target_note"]["id"]} == {str(first.id), str(second.id)}
        assert 0 < item["similarity_score"] <= 1 and "kubernetes" in item["explanation"]
        assert "body" not in str(item)

    def test_is_scoped_to_the_owner(self, client, bob, pending):
        assert client.get("/api/suggestions", headers=bob.headers).json()["total"] == 0

    def test_hides_suggestions_made_stale_by_an_edit_until_they_are_regenerated(
        self, client, alice, pending, edit_note, process
    ):
        first, second, _ = pending
        edit_note(first, body="rolling updates pods services probes extra")
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 0
        process(first, alice)
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 1

    def test_filters_by_note_orders_by_score_and_paginates(self, client, alice, add_note, process):
        base = add_note(alice, "Python testing", "pytest fixtures parametrize mocking coverage")
        best = add_note(alice, "Python testing", "pytest fixtures parametrize mocking coverage tips")
        weaker = add_note(alice, "Python testing basics", "pytest fixtures mocking")
        process(base, alice)
        items = client.get("/api/suggestions", headers=alice.headers).json()["items"]
        scores = [i["similarity_score"] for i in items]
        assert len(items) == 2 and scores == sorted(scores, reverse=True)

        by_note = client.get("/api/suggestions", params={"note_id": str(weaker.id)}, headers=alice.headers).json()
        assert by_note["total"] == 1
        paged = client.get("/api/suggestions", params={"limit": 1, "offset": 1}, headers=alice.headers).json()
        assert paged["total"] == 2 and len(paged["items"]) == 1
        assert best.id

    @pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"note_id": "nope"}])
    def test_invalid_parameters_return_400(self, client, alice, params):
        assert client.get("/api/suggestions", params=params, headers=alice.headers).status_code == 400


class TestAccept:
    def test_creates_one_canonical_link_visible_from_both_notes(self, client, alice, pending, session_factory):
        first, second, suggestion = pending
        response = client.post(f"/api/suggestions/{suggestion.id}/accept", headers=alice.headers)
        assert response.status_code == 201
        link = response.json()
        assert (link["source_note"]["id"], link["target_note"]["id"]) == tuple(
            map(str, canonical_pair(first.id, second.id))
        )

        assert link_count(session_factory) == 1
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 0
        for note in (first, second):
            visible = client.get("/api/links", params={"note_id": str(note.id)}, headers=alice.headers).json()
            assert [i["id"] for i in visible["items"]] == [link["id"]]

    def test_repeating_the_action_creates_no_duplicate(self, client, alice, pending, session_factory):
        _, _, suggestion = pending
        url = f"/api/suggestions/{suggestion.id}/accept"
        assert client.post(url, headers=alice.headers).status_code == 201
        again = client.post(url, headers=alice.headers)
        assert again.status_code == 404 and "already" in again.json()["detail"]
        assert link_count(session_factory) == 1

    def test_an_existing_link_is_returned_rather_than_duplicated(self, client, alice, pending, session_factory):
        first, second, suggestion = pending
        low, high = canonical_pair(first.id, second.id)
        with session_factory() as db:
            db.add(AcceptedLink(source_note_id=low, target_note_id=high, owner_id=alice.id))
            db.commit()
        response = client.post(f"/api/suggestions/{suggestion.id}/accept", headers=alice.headers)
        assert response.status_code == 200
        assert link_count(session_factory) == 1

    def test_stale_suggestion_is_rejected_with_409_and_left_for_regeneration(
        self, client, alice, pending, edit_note, process, session_factory, suggestions
    ):
        first, _, suggestion = pending
        edit_note(first, body="rolling updates pods services probes extra")
        response = client.post(f"/api/suggestions/{suggestion.id}/accept", headers=alice.headers)
        assert response.status_code == 409 and "stale" in response.json()["detail"]
        assert link_count(session_factory) == 0

        process(first, alice)
        (fresh,) = suggestions()
        assert client.post(f"/api/suggestions/{fresh.id}/accept", headers=alice.headers).status_code == 201

    def test_other_users_suggestions_look_nonexistent(self, client, bob, pending, session_factory):
        _, _, suggestion = pending
        response = client.post(f"/api/suggestions/{suggestion.id}/accept", headers=bob.headers)
        assert response.status_code == 404
        assert link_count(session_factory) == 0

    def test_unknown_and_malformed_ids(self, client, alice):
        assert client.post(f"/api/suggestions/{uuid4()}/accept", headers=alice.headers).status_code == 404
        assert client.post("/api/suggestions/not-a-uuid/accept", headers=alice.headers).status_code == 400

    def test_rejected_suggestions_cannot_be_accepted(self, client, alice, pending):
        _, _, suggestion = pending
        client.post(f"/api/suggestions/{suggestion.id}/reject", headers=alice.headers)
        assert client.post(f"/api/suggestions/{suggestion.id}/accept", headers=alice.headers).status_code == 404


class TestReject:
    def test_removes_it_from_the_pending_list_without_creating_a_link(self, client, alice, pending, session_factory):
        _, _, suggestion = pending
        assert client.post(f"/api/suggestions/{suggestion.id}/reject", headers=alice.headers).status_code == 204
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 0
        assert link_count(session_factory) == 0
        with session_factory() as db:
            row = db.get(Suggestion, suggestion.id)
            assert row.status == "rejected" and row.rejected_at is not None

    def test_stays_rejected_when_the_notes_are_reprocessed_but_returns_after_an_edit(
        self, client, alice, pending, process, edit_note
    ):
        first, second, suggestion = pending
        client.post(f"/api/suggestions/{suggestion.id}/reject", headers=alice.headers)
        process(second, alice)
        process(first, alice)
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 0

        edit_note(second, body="kubernetes rolling updates pods services extra")
        process(second, alice)
        assert client.get("/api/suggestions", headers=alice.headers).json()["total"] == 1

    def test_repeat_rejection_and_foreign_rejection_are_404(self, client, alice, bob, pending):
        _, _, suggestion = pending
        url = f"/api/suggestions/{suggestion.id}/reject"
        assert client.post(url, headers=bob.headers).status_code == 404
        assert client.post(url, headers=alice.headers).status_code == 204
        assert client.post(url, headers=alice.headers).status_code == 404

    def test_stale_suggestion_cannot_be_rejected(self, client, alice, pending, edit_note):
        first, _, suggestion = pending
        edit_note(first, body="rolling updates pods services probes extra")
        assert client.post(f"/api/suggestions/{suggestion.id}/reject", headers=alice.headers).status_code == 409


class TestLinks:
    def test_listing_is_scoped_to_the_owner_and_paginated(self, client, alice, bob, add_note, session_factory):
        notes = [add_note(alice, f"Note {i}", "body") for i in range(4)]
        with session_factory() as db:
            for other in notes[1:]:
                low, high = canonical_pair(notes[0].id, other.id)
                db.add(AcceptedLink(source_note_id=low, target_note_id=high, owner_id=alice.id, created_at=utcnow()))
            db.commit()
        page = client.get("/api/links", params={"limit": 2}, headers=alice.headers).json()
        assert page["total"] == 3 and len(page["items"]) == 2
        assert client.get("/api/links", headers=bob.headers).json()["total"] == 0
        assert (
            client.get("/api/links", params={"note_id": str(notes[1].id)}, headers=alice.headers).json()["total"] == 1
        )
