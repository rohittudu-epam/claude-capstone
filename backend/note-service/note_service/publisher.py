"""Outbox publisher: relays committed outbox rows to the Redis stream.

Delivery is at-least-once. A crash between XADD and the commit that marks a row published re-sends
that row on restart; consumers dedupe on `event_id`. Run a single instance: `SKIP LOCKED` keeps
concurrent instances from double-sending, but would not preserve ordering across them.
"""

import logging
import signal
import threading
from collections.abc import Callable
from typing import Any

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.db import get_sessionmaker
from shared.events import STREAM_NOTE_EVENTS, NoteEvent
from shared.models import OutboxEntry
from shared.redis_client import create_redis
from shared.timeutil import utcnow

logger = logging.getLogger("note_service.publisher")

MAX_BACKOFF_SECONDS = 30.0


class OutboxPublisher:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        redis: Redis,
        *,
        batch_size: int = 100,
        stream: str = STREAM_NOTE_EVENTS,
        stream_maxlen: int = 100_000,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis
        self._batch_size = batch_size
        self._stream = stream
        self._stream_maxlen = stream_maxlen

    def publish_pending(self) -> int:
        """Publish up to one batch in creation order. Returns the number published.

        A Redis failure stops the batch, keeps the failed row unpublished, and re-raises; rows
        already sent in this batch stay marked.
        """
        with self._session_factory() as db:
            rows = db.scalars(
                select(OutboxEntry)
                .where(OutboxEntry.published_at.is_(None))
                .order_by(OutboxEntry.created_at, OutboxEntry.id)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            ).all()
            published = 0
            try:
                for row in rows:
                    event = NoteEvent.model_validate_json(row.payload)
                    fields: dict[Any, Any] = event.to_stream_fields()
                    self._redis.xadd(self._stream, fields, maxlen=self._stream_maxlen, approximate=True)
                    row.published_at = utcnow()
                    published += 1
            finally:
                db.commit()
            return published

    def run_forever(self, stop: threading.Event, poll_interval: float) -> None:
        failures = 0
        while not stop.is_set():
            try:
                published = self.publish_pending()
            except (RedisError, SQLAlchemyError) as exc:
                failures += 1
                delay = min(MAX_BACKOFF_SECONDS, poll_interval * 2**failures)
                logger.warning(
                    "outbox publish failed; events stay queued and will be retried",
                    extra={"error": type(exc).__name__, "consecutive_failures": failures, "retry_in_seconds": delay},
                )
                stop.wait(delay)
                continue
            if failures:
                logger.info("outbox publishing recovered", extra={"after_failures": failures})
                failures = 0
            if published:
                logger.info("outbox events published", extra={"count": published})
            if published < self._batch_size:
                stop.wait(poll_interval)


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    publisher = OutboxPublisher(
        get_sessionmaker(),
        create_redis(),
        batch_size=settings.outbox_batch_size,
        stream_maxlen=settings.note_events_stream_maxlen,
    )
    logger.info("outbox publisher started")
    publisher.run_forever(stop, settings.outbox_poll_interval_seconds)
    logger.info("outbox publisher stopped")


if __name__ == "__main__":
    main()
