"""Redis Streams consumer for note events.

Guarantees and limits:
- At-least-once: a message is acknowledged only after its handler succeeds. Failed messages stay
  pending and are re-claimed once idle, up to `max_deliveries`, then moved to the dead-letter stream.
- Duplicates (the publisher is at-least-once too) are skipped by `event_id`, and handlers must still
  be idempotent because that check is best effort (a crash can precede the dedupe write).
- Malformed events and unsupported schema versions are dead-lettered immediately, never retried.
- Retries can reorder events for one note, so handlers must read current note state from the
  database rather than trust arrival order.
"""

import logging
import threading
from collections.abc import Callable, Iterable
from typing import Any

from redis import Redis
from redis.exceptions import RedisError, ResponseError

from shared.events import STREAM_NOTE_EVENTS, STREAM_NOTE_EVENTS_DEAD, EventSchemaError, NoteEvent
from shared.heartbeat import touch_heartbeat
from shared.jsonlog import correlation_context
from shared.timeutil import utcnow

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 30.0

Handler = Callable[[NoteEvent], None]
Entries = Iterable[tuple[str, dict[str, str] | None]]


class NoteEventConsumer:
    def __init__(
        self,
        redis: Redis,
        handler: Handler,
        *,
        consumer_name: str,
        group: str = "link-service",
        stream: str = STREAM_NOTE_EVENTS,
        dead_stream: str = STREAM_NOTE_EVENTS_DEAD,
        batch_size: int = 10,
        block_ms: int = 5000,
        claim_idle_ms: int = 60_000,
        max_deliveries: int = 5,
        dedupe_ttl_seconds: int = 86_400,
    ) -> None:
        self._redis = redis
        self._handler = handler
        self._consumer = consumer_name
        self._group = group
        self._stream = stream
        self._dead_stream = dead_stream
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._claim_idle_ms = claim_idle_ms
        self._max_deliveries = max_deliveries
        self._dedupe_ttl = dedupe_ttl_seconds

    def ensure_group(self) -> None:
        try:
            self._redis.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def poll_once(self) -> int:
        """Handle stale pending messages, then new ones. Returns the number of entries examined."""
        examined = self._handle(self._claim_stale())
        response: Any = self._redis.xreadgroup(
            self._group, self._consumer, {self._stream: ">"}, count=self._batch_size, block=self._block_ms
        )
        fresh: list[tuple[str, dict[str, str] | None]] = response[0][1] if response else []
        return examined + self._handle(fresh)

    def run_forever(self, stop: threading.Event) -> None:
        failures = 0
        group_ready = False
        while not stop.is_set():
            touch_heartbeat()
            try:
                if not group_ready:
                    self.ensure_group()
                    group_ready = True
                self.poll_once()
            except RedisError as exc:
                failures += 1
                group_ready = False  # the stream or group may have been lost; re-create on recovery
                delay = min(MAX_BACKOFF_SECONDS, 0.5 * 2**failures)
                logger.warning(
                    "event consumer cannot reach redis; retrying",
                    extra={"error": type(exc).__name__, "consecutive_failures": failures, "retry_in_seconds": delay},
                )
                stop.wait(delay)
                continue
            if failures:
                logger.info("event consumer recovered", extra={"after_failures": failures})
                failures = 0

    def _claim_stale(self) -> list[tuple[str, dict[str, str] | None]]:
        result: Any = self._redis.xautoclaim(
            self._stream,
            self._group,
            self._consumer,
            min_idle_time=self._claim_idle_ms,
            start_id="0-0",
            count=self._batch_size,
        )
        return list(result[1])

    def _handle(self, entries: Entries) -> int:
        count = 0
        for message_id, fields in entries:
            count += 1
            if fields is None:  # entry was trimmed from the stream while pending
                self._ack(message_id)
                continue
            try:
                event = NoteEvent.from_stream_fields(fields)
            except EventSchemaError as exc:
                self._dead_letter(message_id, fields, f"unreadable event: {exc}")
                continue
            with correlation_context(event.correlation_id or event.event_id.hex):
                self._process(message_id, fields, event)
        return count

    def _process(self, message_id: str, fields: dict[str, str], event: NoteEvent) -> None:
        dedupe_key = f"{self._stream}:processed:{self._group}:{event.event_id}"
        if self._redis.exists(dedupe_key):
            logger.info("duplicate note event skipped", extra={"event_id": str(event.event_id)})
            self._ack(message_id)
            return
        try:
            self._handler(event)
        except Exception as exc:
            deliveries = self._times_delivered(message_id)
            if deliveries >= self._max_deliveries:
                self._dead_letter(message_id, fields, f"handler failed {deliveries} times: {type(exc).__name__}")
            else:
                logger.warning(
                    "note event handler failed; will retry",
                    extra={"event_id": str(event.event_id), "error": type(exc).__name__, "delivery": deliveries},
                    exc_info=True,
                )
            return
        self._redis.set(dedupe_key, "1", ex=self._dedupe_ttl)
        self._ack(message_id)
        logger.info(
            "note event processed",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type.value,
                "note_id": str(event.note_id),
            },
        )

    def _times_delivered(self, message_id: str) -> int:
        pending = self._redis.xpending_range(self._stream, self._group, min=message_id, max=message_id, count=1)
        return int(pending[0]["times_delivered"]) if pending else 1

    def _ack(self, message_id: str) -> None:
        self._redis.xack(self._stream, self._group, message_id)

    def _dead_letter(self, message_id: str, fields: dict[str, str], reason: str) -> None:
        entry: dict[Any, Any] = {
            **fields,
            "original_id": message_id,
            "reason": reason,
            "dead_lettered_at": utcnow().isoformat(),
        }
        self._redis.xadd(self._dead_stream, entry)
        self._ack(message_id)
        logger.error("note event moved to dead-letter stream", extra={"message_id": message_id, "reason": reason})
