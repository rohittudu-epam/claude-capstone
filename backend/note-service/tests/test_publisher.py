import threading
import time
from uuid import uuid4

import fakeredis
import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select

from note_service.publisher import OutboxPublisher
from shared.events import STREAM_NOTE_EVENTS, EventSchemaError, NoteEvent, NoteEventType
from shared.models import OutboxEntry
from shared.outbox import add_note_event
from shared.timeutil import utcnow


@pytest.fixture
def owner(make_user):
    return make_user("owner@example.com")


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


def queue_events(session_factory, owner, count, event_type=NoteEventType.UPDATED):
    note_ids = []
    with session_factory() as db:
        for _ in range(count):
            note_id = uuid4()
            note_ids.append(note_id)
            add_note_event(db, note_id=note_id, owner_id=owner.id, event_type=event_type, occurred_at=utcnow())
            db.flush()
        db.commit()
    return note_ids


def published_flags(session_factory):
    with session_factory() as db:
        return [e.published_at is not None for e in db.scalars(select(OutboxEntry).order_by(OutboxEntry.created_at))]


class FlakyRedis:
    """Delegates to a real fake client but fails XADD on the listed call numbers."""

    def __init__(self, inner, fail_on):
        self.inner, self.fail_on, self.calls = inner, set(fail_on), 0

    def xadd(self, *args, **kwargs):
        self.calls += 1
        if self.calls in self.fail_on:
            raise RedisConnectionError("redis unavailable")
        return self.inner.xadd(*args, **kwargs)


def test_publishes_in_order_and_marks_rows_published(session_factory, owner, redis):
    note_ids = queue_events(session_factory, owner, 3)
    publisher = OutboxPublisher(session_factory, redis)

    assert publisher.publish_pending() == 3
    entries = redis.xrange(STREAM_NOTE_EVENTS)
    assert [NoteEvent.from_stream_fields(f).note_id for _, f in entries] == note_ids
    assert published_flags(session_factory) == [True, True, True]
    assert publisher.publish_pending() == 0
    assert redis.xlen(STREAM_NOTE_EVENTS) == 3


def test_stream_entries_follow_the_v1_contract_without_note_content(session_factory, owner, redis):
    queue_events(session_factory, owner, 1, NoteEventType.CREATED)
    OutboxPublisher(session_factory, redis).publish_pending()
    ((_, fields),) = redis.xrange(STREAM_NOTE_EVENTS)
    assert set(fields) == {"event_id", "schema_version", "event_type", "note_id", "owner_id", "occurred_at"}
    assert fields["schema_version"] == "1" and fields["event_type"] == "created"
    with session_factory() as db:
        assert fields["event_id"] == str(db.scalar(select(OutboxEntry.id)))


def test_respects_batch_size(session_factory, owner, redis):
    queue_events(session_factory, owner, 5)
    publisher = OutboxPublisher(session_factory, redis, batch_size=2)
    assert [publisher.publish_pending() for _ in range(4)] == [2, 2, 1, 0]


def test_redis_outage_keeps_events_queued_then_delivers_after_recovery(session_factory, owner, redis):
    queue_events(session_factory, owner, 2)
    down = FlakyRedis(redis, fail_on={1})
    publisher = OutboxPublisher(session_factory, down)

    with pytest.raises(RedisConnectionError):
        publisher.publish_pending()
    assert published_flags(session_factory) == [False, False]
    assert redis.xlen(STREAM_NOTE_EVENTS) == 0

    assert publisher.publish_pending() == 2
    assert published_flags(session_factory) == [True, True]


def test_failure_mid_batch_keeps_earlier_rows_marked_and_later_rows_pending(session_factory, owner, redis):
    queue_events(session_factory, owner, 3)
    publisher = OutboxPublisher(session_factory, FlakyRedis(redis, fail_on={2}))

    with pytest.raises(RedisConnectionError):
        publisher.publish_pending()
    assert published_flags(session_factory) == [True, False, False]

    assert publisher.publish_pending() == 2
    assert redis.xlen(STREAM_NOTE_EVENTS) == 3  # nothing lost, nothing duplicated


def test_run_forever_survives_an_outage_and_recovers(session_factory, owner, redis):
    queue_events(session_factory, owner, 2)
    publisher = OutboxPublisher(session_factory, FlakyRedis(redis, fail_on={1, 2}))
    stop = threading.Event()
    thread = threading.Thread(target=publisher.run_forever, args=(stop, 0.01), daemon=True)
    thread.start()
    deadline = time.time() + 10
    while redis.xlen(STREAM_NOTE_EVENTS) < 2 and time.time() < deadline:
        time.sleep(0.05)
    stop.set()
    thread.join(timeout=5)
    assert redis.xlen(STREAM_NOTE_EVENTS) == 2
    assert published_flags(session_factory) == [True, True]


def test_unsupported_schema_version_is_rejected_by_consumers():
    fields = {
        "event_id": str(uuid4()),
        "schema_version": "2",
        "event_type": "created",
        "note_id": str(uuid4()),
        "owner_id": str(uuid4()),
        "occurred_at": utcnow().isoformat(),
    }
    with pytest.raises(EventSchemaError):
        NoteEvent.from_stream_fields(fields)


def test_unknown_extra_fields_are_ignored_for_forward_compatibility():
    fields = {
        "event_id": str(uuid4()),
        "schema_version": "1",
        "event_type": "updated",
        "note_id": str(uuid4()),
        "owner_id": str(uuid4()),
        "occurred_at": utcnow().isoformat(),
        "future": "x",
    }
    assert NoteEvent.from_stream_fields(fields).event_type is NoteEventType.UPDATED
