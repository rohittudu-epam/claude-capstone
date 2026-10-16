import threading
import time
from uuid import uuid4

import fakeredis
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from link_service.consumer import NoteEventConsumer
from note_service.main import app as note_app
from note_service.publisher import OutboxPublisher
from shared.events import STREAM_NOTE_EVENTS, STREAM_NOTE_EVENTS_DEAD, NoteEvent, NoteEventType
from shared.timeutil import utcnow

GROUP = "link-service"


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


def event_fields(event_type="updated", **overrides) -> dict[str, str]:
    fields = {
        "event_id": str(uuid4()),
        "schema_version": "1",
        "event_type": event_type,
        "note_id": str(uuid4()),
        "owner_id": str(uuid4()),
        "occurred_at": utcnow().isoformat(),
    }
    return {**fields, **overrides}


def make_consumer(redis, handler, **kwargs):
    kwargs.setdefault("block_ms", 10)
    kwargs.setdefault("claim_idle_ms", 0)
    consumer = NoteEventConsumer(redis, handler, consumer_name="test-consumer", group=GROUP, **kwargs)
    consumer.ensure_group()
    return consumer


def pending_count(redis) -> int:
    return redis.xpending(STREAM_NOTE_EVENTS, GROUP)["pending"]


class Recorder:
    def __init__(self, fail_times=0):
        self.events: list[NoteEvent] = []
        self.fail_times = fail_times
        self.attempts = 0

    def __call__(self, event: NoteEvent) -> None:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise RuntimeError("boom")
        self.events.append(event)


class TestSetup:
    def test_ensure_group_is_idempotent_and_creates_the_stream(self, redis):
        consumer = NoteEventConsumer(redis, Recorder(), consumer_name="c", group=GROUP)
        consumer.ensure_group()
        consumer.ensure_group()
        assert redis.xinfo_groups(STREAM_NOTE_EVENTS)[0]["name"] == GROUP

    def test_idle_poll_returns_zero(self, redis):
        assert make_consumer(redis, Recorder()).poll_once() == 0


class TestProcessing:
    def test_processes_in_order_and_acknowledges(self, redis):
        recorder = Recorder()
        consumer = make_consumer(redis, recorder)
        sent = [event_fields(note_id=str(uuid4())) for _ in range(4)]
        for fields in sent:
            redis.xadd(STREAM_NOTE_EVENTS, fields)

        assert consumer.poll_once() == 4
        assert [str(e.note_id) for e in recorder.events] == [f["note_id"] for f in sent]
        assert pending_count(redis) == 0
        assert consumer.poll_once() == 0  # offsets advanced: nothing is redelivered

    def test_a_restarted_consumer_continues_from_the_group_offset(self, redis):
        first = Recorder()
        make_consumer(redis, first).poll_once()
        redis.xadd(STREAM_NOTE_EVENTS, event_fields())
        make_consumer(redis, first).poll_once()
        redis.xadd(STREAM_NOTE_EVENTS, event_fields())
        second = Recorder()
        make_consumer(redis, second).poll_once()
        assert len(first.events) == 1 and len(second.events) == 1

    def test_handles_every_event_type(self, redis):
        recorder = Recorder()
        for event_type in ("created", "updated", "deleted"):
            redis.xadd(STREAM_NOTE_EVENTS, event_fields(event_type))
        make_consumer(redis, recorder).poll_once()
        assert [e.event_type for e in recorder.events] == list(NoteEventType)

    def test_duplicate_delivery_is_handled_once(self, redis):
        recorder = Recorder()
        fields = event_fields()
        redis.xadd(STREAM_NOTE_EVENTS, fields)
        redis.xadd(STREAM_NOTE_EVENTS, fields)  # publisher retry re-sent the same event_id
        consumer = make_consumer(redis, recorder)
        consumer.poll_once()
        assert len(recorder.events) == 1
        assert pending_count(redis) == 0


class TestFailureHandling:
    def test_failed_event_stays_pending_then_succeeds_on_retry(self, redis):
        recorder = Recorder(fail_times=2)
        redis.xadd(STREAM_NOTE_EVENTS, event_fields())
        consumer = make_consumer(redis, recorder)

        consumer.poll_once()
        assert recorder.events == [] and pending_count(redis) == 1
        consumer.poll_once()
        assert recorder.events == [] and pending_count(redis) == 1
        consumer.poll_once()
        assert len(recorder.events) == 1 and pending_count(redis) == 0
        assert redis.xlen(STREAM_NOTE_EVENTS_DEAD) == 0

    def test_event_is_not_retried_before_it_has_been_idle_long_enough(self, redis):
        recorder = Recorder(fail_times=1)
        redis.xadd(STREAM_NOTE_EVENTS, event_fields())
        consumer = make_consumer(redis, recorder, claim_idle_ms=60_000)
        consumer.poll_once()
        consumer.poll_once()
        assert recorder.attempts == 1

    def test_event_that_keeps_failing_is_dead_lettered_with_its_reason(self, redis):
        recorder = Recorder(fail_times=100)
        fields = event_fields()
        redis.xadd(STREAM_NOTE_EVENTS, fields)
        consumer = make_consumer(redis, recorder, max_deliveries=3)

        for _ in range(3):
            consumer.poll_once()
        assert recorder.attempts == 3
        assert pending_count(redis) == 0
        ((_, dead),) = redis.xrange(STREAM_NOTE_EVENTS_DEAD)
        assert dead["event_id"] == fields["event_id"]
        assert "handler failed 3 times" in dead["reason"] and "RuntimeError" in dead["reason"]
        consumer.poll_once()
        assert recorder.attempts == 3  # no further attempts

    @pytest.mark.parametrize(
        "fields",
        [
            event_fields(schema_version="2"),
            event_fields(event_type="exploded"),
            {"event_id": "not-a-uuid"},
            {},
        ],
    )
    def test_unreadable_events_are_dead_lettered_without_calling_the_handler(self, redis, fields):
        recorder = Recorder()
        redis.xadd(STREAM_NOTE_EVENTS, fields or {"junk": "1"})
        make_consumer(redis, recorder).poll_once()
        assert recorder.attempts == 0
        assert redis.xlen(STREAM_NOTE_EVENTS_DEAD) == 1
        assert pending_count(redis) == 0

    def test_a_poison_message_does_not_block_later_events(self, redis):
        recorder = Recorder()
        redis.xadd(STREAM_NOTE_EVENTS, {"junk": "1"})
        good = event_fields()
        redis.xadd(STREAM_NOTE_EVENTS, good)
        make_consumer(redis, recorder).poll_once()
        assert [str(e.event_id) for e in recorder.events] == [good["event_id"]]


class FlakyRedis:
    """Raises on the first N xreadgroup calls, as a dropped connection would."""

    def __init__(self, inner, failures):
        self.inner, self.failures = inner, failures

    def xreadgroup(self, *args, **kwargs):
        if self.failures > 0:
            self.failures -= 1
            raise RedisConnectionError("connection lost")
        return self.inner.xreadgroup(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.inner, name)


def test_run_forever_survives_connection_failures_and_resumes(redis, monkeypatch):
    monkeypatch.setattr("link_service.consumer.MAX_BACKOFF_SECONDS", 0.05)
    recorder = Recorder()
    fields = event_fields()
    redis.xadd(STREAM_NOTE_EVENTS, fields)
    consumer = make_consumer(FlakyRedis(redis, failures=2), recorder)
    stop = threading.Event()
    thread = threading.Thread(target=consumer.run_forever, args=(stop,), daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not recorder.events and time.time() < deadline:
        time.sleep(0.05)
    stop.set()
    thread.join(timeout=5)
    assert [str(e.event_id) for e in recorder.events] == [fields["event_id"]]


def test_end_to_end_note_api_to_outbox_to_stream_to_consumer(session_factory, make_user, redis):
    user = make_user("flow@example.com")
    client = TestClient(note_app)
    created = client.post("/api/notes", json={"title": "Flow", "body": "text"}, headers=user.headers).json()
    note_url = f"/api/notes/{created['id']}"
    client.put(note_url, json={"title": "Flow", "body": "edited"}, headers=user.headers)
    client.delete(note_url, headers=user.headers)

    assert OutboxPublisher(session_factory, redis).publish_pending() == 3
    recorder = Recorder()
    make_consumer(redis, recorder).poll_once()

    assert [e.event_type for e in recorder.events] == [
        NoteEventType.CREATED,
        NoteEventType.UPDATED,
        NoteEventType.DELETED,
    ]
    assert {str(e.note_id) for e in recorder.events} == {created["id"]}
    assert {e.owner_id for e in recorder.events} == {user.id}
    assert pending_count(redis) == 0
