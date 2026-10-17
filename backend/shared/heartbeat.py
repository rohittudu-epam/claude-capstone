"""Liveness marker for processes with no HTTP port (the outbox publisher and the link worker).

The process touches the file on every loop iteration, including while backing off from a Redis or database
failure, so a stale file means the loop is hung or dead. Docker's healthcheck compares its age to a limit.
"""

import logging
from pathlib import Path

from shared.config import get_settings

logger = logging.getLogger(__name__)


def touch_heartbeat() -> None:
    path = get_settings().heartbeat_file
    if not path:
        return
    try:
        Path(path).touch()
    except OSError:
        logger.warning("could not update heartbeat file")
