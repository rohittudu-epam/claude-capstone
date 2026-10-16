import random
import time
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert

from note_service.main import app
from shared.models import Note
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


def create(client, user, title, body="", tags=None):
    response = client.post("/api/notes", json={"title": title, "body": body, "tags": tags or []}, headers=user.headers)
    assert response.status_code == 201, response.text
    return response.json()


def search(client, user, q, **params):
    return client.get("/api/notes/search", params={"q": q, **params}, headers=user.headers)


class TestMatching:
    def test_matches_title_and_body_and_ignores_unrelated(self, client, alice):
        in_title = create(client, alice, "Kubernetes basics", "intro")
        in_body = create(client, alice, "Cluster notes", "we run kubernetes in production")
        create(client, alice, "Cooking", "pasta and sauce")
        body = search(client, alice, "kubernetes").json()
        assert {i["id"] for i in body["items"]} == {in_title["id"], in_body["id"]}
        assert body["total"] == 2

    def test_title_matches_rank_above_body_only_matches(self, client, alice):
        body_only = create(client, alice, "Meeting minutes", "discussed kubernetes kubernetes kubernetes at length")
        title_match = create(client, alice, "Kubernetes", "short")
        items = search(client, alice, "kubernetes").json()["items"]
        assert [i["id"] for i in items] == [title_match["id"], body_only["id"]]
        assert items[0]["rank"] > items[1]["rank"] > 0

    def test_stemming_and_websearch_syntax(self, client, alice):
        services = create(client, alice, "Deploying services", "rolling deployments")
        databases = create(client, alice, "Deploying databases", "backups")
        create(client, alice, "Cooking", "pasta")
        stemmed = search(client, alice, "deployment").json()["items"]  # "deploying" and "deployment" share a stem
        assert {i["id"] for i in stemmed} == {services["id"], databases["id"]}
        excluded = search(client, alice, "deploying -databases").json()["items"]
        assert [i["id"] for i in excluded] == [services["id"]]
        phrase = search(client, alice, '"rolling deployments"').json()["items"]
        assert [i["id"] for i in phrase] == [services["id"]]

    @pytest.mark.parametrize("q", ["the", "!!!", "'; DROP TABLE notes; --", "a & b | (c", "\\"])
    def test_hostile_or_meaningless_queries_do_not_error(self, client, alice, q):
        create(client, alice, "Anything", "body")
        response = search(client, alice, q)
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_results_contain_metadata_but_never_the_body(self, client, alice):
        note = create(client, alice, "Findable", "very private body content", tags=["x"])
        item = search(client, alice, "findable").json()["items"][0]
        assert set(item) == {"id", "owner_id", "title", "tags", "updated_at", "rank"}
        assert item["id"] == note["id"] and item["owner_id"] == str(alice.id) and item["tags"] == ["x"]
        assert "private" not in search(client, alice, "findable").text

    def test_updated_content_is_searchable_and_old_content_is_not(self, client, alice):
        note = create(client, alice, "Draft", "alpha")
        client.put(f"/api/notes/{note['id']}", json={"title": "Draft", "body": "omega"}, headers=alice.headers)
        assert search(client, alice, "alpha").json()["items"] == []
        assert len(search(client, alice, "omega").json()["items"]) == 1

    def test_pagination(self, client, alice):
        for i in range(5):
            create(client, alice, f"Python tip {i}")
        page = search(client, alice, "python", limit=2, offset=4).json()
        assert page["total"] == 5 and len(page["items"]) == 1
        assert search(client, alice, "python", limit=2).json()["limit"] == 2


class TestIsolationAndFilters:
    def test_results_are_restricted_to_the_requesting_user(self, client, alice, bob):
        create(client, alice, "Alice kubernetes")
        mine = create(client, bob, "Bob kubernetes")
        body = search(client, bob, "kubernetes").json()
        assert [i["id"] for i in body["items"]] == [mine["id"]] and body["total"] == 1

    def test_tag_filter_uses_and_semantics(self, client, alice):
        both = create(client, alice, "Docker both", tags=["devops", "backend"])
        create(client, alice, "Docker one", tags=["devops"])
        create(client, alice, "Docker none")
        assert len(search(client, alice, "docker").json()["items"]) == 3
        assert [i["id"] for i in search(client, alice, "docker", tags="devops,backend").json()["items"]] == [both["id"]]
        assert search(client, alice, "docker", tags="devops,missing").json()["items"] == []

    def test_another_users_tags_do_not_widen_results(self, client, alice, bob):
        create(client, alice, "Docker", tags=["devops"])
        assert search(client, bob, "docker", tags="devops").json()["items"] == []


class TestContract:
    @pytest.mark.parametrize("q", ["", "   "])
    def test_empty_query_is_a_400(self, client, alice, q):
        response = search(client, alice, q)
        assert response.status_code == 400

    def test_missing_or_oversized_query_is_a_400(self, client, alice):
        assert client.get("/api/notes/search", headers=alice.headers).status_code == 400
        assert search(client, alice, "x" * 201).status_code == 400

    def test_search_route_is_not_shadowed_by_note_id_route(self, client, alice):
        assert search(client, alice, "anything").status_code == 200


def test_search_over_10k_notes_meets_the_500ms_p95_target(client, alice, session_factory):
    rng = random.Random(7)
    vocabulary = [f"word{i}" for i in range(3000)]
    now = utcnow()
    rows = []
    for i in range(10_000):
        words = rng.sample(vocabulary, 40)
        if i % 500 == 0:
            words.append("kubernetes")
        rows.append(
            {
                "id": uuid4(),
                "owner_id": alice.id,
                "title": f"Note {i} {words[0]}",
                "body": " ".join(words),
                "created_at": now,
                "updated_at": now,
            }
        )
    with session_factory() as db:
        db.execute(insert(Note), rows)
        db.commit()

    timings = []
    for _ in range(20):
        start = time.perf_counter()
        response = search(client, alice, "kubernetes")
        timings.append(time.perf_counter() - start)
        assert response.status_code == 200 and response.json()["total"] == 20
    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1]
    print(f"\nsearch p95 over 10k notes: {p95 * 1000:.0f} ms (median {timings[10] * 1000:.0f} ms)")
    assert p95 < 0.5
