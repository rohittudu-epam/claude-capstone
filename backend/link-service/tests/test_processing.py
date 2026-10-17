from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, update

from link_service import processing
from shared.config import get_settings
from shared.events import NoteEventType
from shared.links import canonical_pair
from shared.models import AcceptedLink, Note, Suggestion
from shared.timeutil import utcnow

K8S_BODY = "rolling updates for kubernetes deployment pods and services with health probes"
K8S_TITLE = "Kubernetes deployment strategies"


class TestGeneration:
    def test_similar_note_gets_a_pending_suggestion_with_score_and_explanation(
        self, alice, add_note, process, suggestions
    ):
        first = add_note(alice)
        second = add_note(alice, "Kubernetes deployments", "kubernetes deployment rolling updates services")
        process(second, alice)

        (suggestion,) = suggestions()
        assert {suggestion.source_note_id, suggestion.target_note_id} == {first.id, second.id}
        assert (suggestion.source_note_id, suggestion.target_note_id) == canonical_pair(first.id, second.id)
        assert suggestion.status == "pending" and suggestion.owner_id == alice.id
        assert suggestion.similarity_score >= get_settings().link_suggestion_threshold
        assert "kubernetes" in suggestion.explanation and "keyword overlap" in suggestion.explanation

    def test_records_the_note_versions_it_was_computed_from(self, alice, add_note, process, suggestions):
        first = add_note(alice)
        second = add_note(alice)
        process(second, alice)
        (suggestion,) = suggestions()
        versions = {first.id: first.updated_at, second.id: second.updated_at}
        assert suggestion.source_updated_at == versions[suggestion.source_note_id]
        assert suggestion.target_updated_at == versions[suggestion.target_note_id]

    def test_unrelated_notes_get_no_suggestion(self, alice, add_note, process, suggestions):
        add_note(alice)
        other = add_note(alice, "Sourdough baking", "flour water salt starter oven crust")
        process(other, alice)
        assert suggestions() == []

    def test_a_single_shared_keyword_is_not_enough(self, alice, add_note, process, suggestions):
        add_note(alice, "Kubernetes", "")
        other = add_note(alice, "Kubernetes", "")
        process(other, alice)
        assert suggestions() == []
        process(other, alice, link_suggestion_min_shared_keywords=1)
        assert len(suggestions()) == 1

    def test_threshold_is_configurable(self, alice, add_note, process, suggestions):
        add_note(alice, "Docker networking", "bridge overlay host drivers containers")
        partial = add_note(alice, "Docker storage", "volumes bind mounts drivers containers")
        process(partial, alice, link_suggestion_threshold=0.9)
        assert suggestions() == []
        process(partial, alice, link_suggestion_threshold=0.1)
        assert len(suggestions()) == 1

    def test_keeps_only_the_best_matches_up_to_the_cap(self, alice, add_note, process, suggestions):
        source = add_note(alice, "Python testing", "pytest fixtures parametrize mocking coverage")
        closest = add_note(alice, "Python testing", "pytest fixtures parametrize mocking coverage tips")
        close = add_note(alice, "Python testing basics", "pytest fixtures")
        add_note(alice, "Python packaging", "python testing wheels sdist build backend")
        process(source, alice, link_suggestion_max_per_note=2, link_suggestion_threshold=0.1)
        kept = {s.source_note_id if s.target_note_id == source.id else s.target_note_id for s in suggestions()}
        assert len(kept) == 2 and closest.id in kept and close.id in kept


class TestExclusions:
    def test_never_suggests_a_note_for_itself(self, alice, add_note, process, suggestions):
        only = add_note(alice)
        process(only, alice)
        assert suggestions() == []

    def test_never_crosses_owners(self, alice, bob, add_note, process, suggestions):
        add_note(bob)
        mine = add_note(alice)
        process(mine, alice)
        assert suggestions() == []

    def test_skips_pairs_that_are_already_linked(self, alice, add_note, process, suggestions, session_factory):
        first, second = add_note(alice), add_note(alice)
        low, high = canonical_pair(first.id, second.id)
        with session_factory() as db:
            db.add(AcceptedLink(source_note_id=low, target_note_id=high, owner_id=alice.id))
            db.commit()
        process(second, alice)
        assert suggestions() == []

    def test_deleted_notes_are_not_candidates_and_take_their_suggestions_with_them(
        self, alice, add_note, process, suggestions, session_factory
    ):
        first, second = add_note(alice), add_note(alice)
        process(second, alice)
        assert len(suggestions()) == 1
        with session_factory() as db:
            db.execute(delete(Note).where(Note.id == first.id))
            db.commit()
        assert suggestions() == []
        process(second, alice)
        assert suggestions() == []

    def test_events_for_missing_notes_or_wrong_owners_are_ignored(self, alice, bob, add_note, process, suggestions):
        add_note(alice)
        mine = add_note(alice)
        ghost = Note(id=uuid4(), owner_id=alice.id, title="gone", body="", created_at=utcnow(), updated_at=utcnow())
        process(ghost, alice)
        process(mine, bob)  # event claims the wrong owner
        assert suggestions() == []

    def test_delete_events_do_nothing(self, alice, add_note, process, suggestions):
        add_note(alice)
        note = add_note(alice)
        process(note, alice, NoteEventType.DELETED)
        assert suggestions() == []


class TestIdempotencyAndRetry:
    def test_reprocessing_does_not_duplicate_or_churn_suggestions(self, alice, add_note, process, suggestions):
        add_note(alice)
        note = add_note(alice)
        process(note, alice)
        before = suggestions()
        for _ in range(3):
            process(note, alice)
        after = suggestions()
        assert len(after) == 1
        assert (after[0].id, after[0].created_at) == (before[0].id, before[0].created_at)

    def test_processing_either_side_of_a_pair_yields_the_same_single_suggestion(
        self, alice, add_note, process, suggestions
    ):
        first, second = add_note(alice), add_note(alice)
        process(first, alice)
        process(second, alice)
        assert len(suggestions()) == 1

    def test_a_failure_part_way_leaves_nothing_behind_and_a_retry_succeeds(
        self, alice, add_note, process, suggestions, monkeypatch
    ):
        add_note(alice)
        add_note(alice)
        note = add_note(alice)
        real = processing.canonical_pair
        calls = []

        def flaky(a, b):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("analysis crashed")
            return real(a, b)

        monkeypatch.setattr(processing, "canonical_pair", flaky)
        with pytest.raises(RuntimeError):
            process(note, alice)
        assert suggestions() == []  # the first upsert was rolled back with the failed transaction

        monkeypatch.setattr(processing, "canonical_pair", real)
        process(note, alice)
        assert len(suggestions()) == 2


class TestChangingNotes:
    def test_suggestion_is_dropped_when_an_edit_makes_the_notes_unrelated(
        self, alice, add_note, edit_note, process, suggestions
    ):
        add_note(alice)
        note = add_note(alice)
        process(note, alice)
        assert len(suggestions()) == 1
        edit_note(note, title="Sourdough baking", body="flour water salt starter oven crust")
        process(note, alice)
        assert suggestions() == []

    def test_suggestion_is_refreshed_with_new_versions_when_still_similar(
        self, alice, add_note, edit_note, process, suggestions
    ):
        add_note(alice)
        note = add_note(alice)
        process(note, alice)
        (old,) = suggestions()
        edit_note(note, body=K8S_BODY + " observability")
        process(note, alice)
        (new,) = suggestions()
        assert new.id == old.id
        assert max(new.source_updated_at, new.target_updated_at) > max(old.source_updated_at, old.target_updated_at)

    def test_a_rejection_survives_reprocessing_until_a_note_changes(
        self, alice, add_note, edit_note, process, suggestions, session_factory
    ):
        add_note(alice)
        note = add_note(alice)
        process(note, alice)
        with session_factory() as db:
            db.execute(update(Suggestion).values(status="rejected", rejected_at=utcnow()))
            db.commit()

        process(note, alice)  # duplicate or retried delivery
        assert [s.status for s in suggestions()] == ["rejected"]

        edit_note(note, body=K8S_BODY + " observability")  # either endpoint changing lifts the suppression
        process(note, alice)
        (revived,) = suggestions()
        assert revived.status == "pending" and revived.rejected_at is None

    def test_an_obsolete_rejection_is_removed_when_the_pair_no_longer_matches(
        self, alice, add_note, edit_note, process, suggestions, session_factory
    ):
        add_note(alice)
        note = add_note(alice)
        process(note, alice)
        with session_factory() as db:
            db.execute(update(Suggestion).values(status="rejected", rejected_at=utcnow()))
            db.commit()
        edit_note(note, title="Sourdough baking", body="flour water salt starter oven crust")
        process(note, alice)
        assert suggestions() == []

    def test_other_pairs_are_untouched_when_one_note_changes(self, alice, add_note, edit_note, process, suggestions):
        a, b = add_note(alice), add_note(alice)
        c = add_note(alice, "Sourdough baking", "flour water salt starter oven crust")
        d = add_note(alice, "Sourdough starter", "flour water salt starter feeding schedule")
        process(a, alice)
        process(c, alice)
        before = {(s.source_note_id, s.target_note_id): s.id for s in suggestions()}
        assert len(before) == 2
        edit_note(a, body=K8S_BODY + " extra")
        process(a, alice)
        after = {(s.source_note_id, s.target_note_id): s.id for s in suggestions()}
        assert after == before
        assert b.id and d.id


def test_candidate_search_finds_the_needle_among_many_unrelated_notes(alice, session_factory, process, suggestions):
    now = utcnow()
    with session_factory() as db:
        db.add_all(
            Note(
                owner_id=alice.id,
                title=f"Filler {i}",
                body=f"unrelated gardening topic number{i} soil compost",
                created_at=now,
                updated_at=now,
            )
            for i in range(300)
        )
        needle = Note(owner_id=alice.id, title=K8S_TITLE, body=K8S_BODY, created_at=now, updated_at=now)
        source = Note(
            owner_id=alice.id,
            title="Kubernetes deployments",
            body=K8S_BODY,
            created_at=now,
            updated_at=now + timedelta(seconds=1),
        )
        db.add_all([needle, source])
        db.commit()
    process(source, alice)
    (suggestion,) = suggestions()
    assert needle.id in {suggestion.source_note_id, suggestion.target_note_id}
