"""Entry point for the note-event consumer process: `python -m link_service.worker`."""

import logging
import signal
import socket
import threading

from link_service.consumer import NoteEventConsumer
from link_service.processing import make_event_handler
from shared.config import get_settings
from shared.db import get_sessionmaker
from shared.redis_client import create_redis

logger = logging.getLogger("link_service.worker")


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    consumer = NoteEventConsumer(
        # The socket timeout must outlast the blocking read or every idle poll would raise.
        create_redis(socket_timeout=settings.consumer_block_ms / 1000 + 10),
        make_event_handler(get_sessionmaker(), settings),
        consumer_name=socket.gethostname(),
        group=settings.consumer_group,
        block_ms=settings.consumer_block_ms,
        claim_idle_ms=settings.consumer_claim_idle_ms,
        max_deliveries=settings.consumer_max_deliveries,
        dedupe_ttl_seconds=settings.event_dedupe_ttl_seconds,
    )
    logger.info("link-service event consumer started")
    consumer.run_forever(stop)
    logger.info("link-service event consumer stopped")


if __name__ == "__main__":
    main()
