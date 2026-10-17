"""Event durability across the outbox, the stream, and the consumer (IMPL-17).

The `real_redis` tests need a Redis server: set TEST_REDIS_URL (CI does; locally the Compose Redis on
127.0.0.1:6379 works). They use a uniquely named stream per test and delete it afterwards. Without a
reachable server they are skipped, not failed.
"""

import os
from uuid import uuid4

import fakeredis
import pytest
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

from link_service.consumer import NoteEventConsumer
from note_service.publisher import OutboxPublisher
from shared.events import NoteEvent, NoteEventType
from shared.models import OutboxEntry
from shared.outbox import add_note_event
from shared.timeutil import utcnow

GROUP = "durability-tests"


@pytest.fixture
def owner(make_user):
    return make_user("durable@example.com")


@pytest.fixture
def real_redis():
    url = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379")
    client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=5)
    try:
        client.ping()
    except Exception:
        pytest.skip(f"no Redis server reachable at {url}")
    stream = f"test_events_{uuid4().hex}"
    yield client, stream
    client.delete(stream, f"{stream}:dead", *client.scan_iter(f"{stream}:processed:*"))


def queue(session_factory, owner, count) -> list:
    note_ids = [uuid4() for _ in range(count)]
    with session_factory() as db:
        for note_id in note_ids:
            add_note_event(
                db, note_id=note_id, owner_id=owner.id, event_type=NoteEventType.UPDATED, occurred_at=utcnow()
            )
            db.flush()
        db.commit()
    return note_ids


def consumer_for(client, stream, handler, name="c1", **kwargs):
    kwargs.setdefault("block_ms", 50)
    kwargs.setdefault("claim_idle_ms", 0)
    consumer = NoteEventConsumer(
        client, handler, consumer_name=name, group=GROUP, stream=stream, dead_stream=f"{stream}:dead", **kwargs
    )
    consumer.ensure_group()
    return consumer


def unpublished(session_factory) -> int:
    with session_factory() as db:
        return len(list(db.scalars(select(OutboxEntry).where(OutboxEntry.published_at.is_(None)))))


def test_unreachable_redis_loses_nothing_and_events_flow_once_it_returns(session_factory, owner):
    note_ids = queue(session_factory, owner, 3)
    dead = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2, decode_responses=True)  # nothing listens here
    with pytest.raises(RedisError):
        OutboxPublisher(session_factory, dead).publish_pending()
    assert unpublished(session_factory) == 3

    recovered = fakeredis.FakeRedis(decode_responses=True)
    assert OutboxPublisher(session_factory, recovered).publish_pending() == 3
    received = []
    consumer_for(recovered, "note_events", received.append).poll_once()
    assert [e.note_id for e in received] == note_ids
    assert unpublished(session_factory) == 0


class TestAgainstRealRedis:
    def test_events_arrive_complete_and_in_order(self, session_factory, owner, real_redis):
        client, stream = real_redis
        note_ids = queue(session_factory, owner, 12)
        assert OutboxPublisher(session_factory, client, stream=stream).publish_pending() == 12
        received: list[NoteEvent] = []
        consumer = consumer_for(client, stream, received.append, batch_size=5)
        while len(received) < 12:
            assert consumer.poll_once() > 0
        assert [e.note_id for e in received] == note_ids
        assert client.xpending(stream, GROUP)["pending"] == 0

    def test_a_crashed_consumer_does_not_lose_its_message(self, session_factory, owner, real_redis):
        client, stream = real_redis
        queue(session_factory, owner, 1)
        OutboxPublisher(session_factory, client, stream=stream).publish_pending()

        def crash(_event):
            raise RuntimeError("worker died mid-processing")

        consumer_for(client, stream, crash, name="doomed").poll_once()
        assert client.xpending(stream, GROUP)["pending"] == 1

        survivor_events: list[NoteEvent] = []
        consumer_for(client, stream, survivor_events.append, name="survivor").poll_once()
        assert len(survivor_events) == 1
        assert client.xpending(stream, GROUP)["pending"] == 0

    def test_a_duplicate_publication_is_processed_once(self, session_factory, owner, real_redis):
        client, stream = real_redis
        queue(session_factory, owner, 1)
        publisher = OutboxPublisher(session_factory, client, stream=stream)
        publisher.publish_pending()
        with session_factory() as db:
            (entry,) = db.scalars(select(OutboxEntry))
            event = NoteEvent.model_validate_json(entry.payload)
        client.xadd(stream, event.to_stream_fields())  # a retry re-sent an event that was in fact delivered
        assert client.xlen(stream) == 2

        received: list[NoteEvent] = []
        consumer_for(client, stream, received.append).poll_once()
        assert len(received) == 1
        assert client.xpending(stream, GROUP)["pending"] == 0

    def test_an_event_that_always_fails_ends_in_the_dead_letter_stream(self, session_factory, owner, real_redis):
        client, stream = real_redis
        queue(session_factory, owner, 1)
        OutboxPublisher(session_factory, client, stream=stream).publish_pending()

        def always_fails(_event):
            raise RuntimeError("poison")

        consumer = consumer_for(client, stream, always_fails, max_deliveries=3)
        for _ in range(4):
            consumer.poll_once()
        assert client.xlen(f"{stream}:dead") == 1
        assert client.xpending(stream, GROUP)["pending"] == 0
        ((_, dead),) = client.xrange(f"{stream}:dead")
        assert "handler failed 3 times" in dead["reason"]
