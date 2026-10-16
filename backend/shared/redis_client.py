"""Redis client factory."""

from redis import Redis

from shared.config import get_settings


def create_redis(socket_timeout: float = 5.0) -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_timeout=socket_timeout,
        socket_connect_timeout=5.0,
        health_check_interval=30,
    )
