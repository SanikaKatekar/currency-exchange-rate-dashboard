"""
Shared async Redis client lifecycle management.

Overview:
    Provides a process-wide Redis connection used by cache, rate limiting, and
    circuit breaker modules. Supports test injection via ``set_redis_client``.

Functions:
    init_redis: Connect to Redis using the configured URL.
    get_redis: Return the active Redis client.
    ping_redis: Return whether Redis responds to PING.
    set_redis_client: Inject a Redis client (used by tests with fakeredis).
    close_redis: Close the connection during application shutdown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging_config import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger("redis")

_redis_client: Redis | None = None


async def init_redis(redis_url: str) -> None:
    """
    Connect to Redis, verify connectivity with PING, and store the client.

    Args:
        redis_url: Redis connection URL (for example ``redis://localhost:6379/0``).

    Returns:
        None.

    Raises:
        Exception: Propagates connection or PING failures to fail fast on startup.
    """
    from redis.asyncio import from_url

    global _redis_client
    logger.info("redis_connect_begin url=%s", redis_url)
    _redis_client = from_url(redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
    await _redis_client.ping()
    logger.info("redis_connect_success url=%s", redis_url)


async def ping_redis() -> bool:
    """
    Return whether the active Redis client responds to PING.

    Returns:
        ``True`` when Redis is reachable, ``False`` on any connection error.
    """
    try:
        redis = get_redis()
        await redis.ping()
        return True
    except Exception as exc:
        logger.warning("redis_ping_failed error=%s", exc)
        return False


def get_redis() -> Redis:
    """
    Return the active Redis client.

    Returns:
        Connected ``redis.asyncio.Redis`` instance.

    Raises:
        RuntimeError: If Redis has not been initialized.
    """
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized")
    return _redis_client


def set_redis_client(client: Redis) -> None:
    """
    Inject a Redis client, typically a ``fakeredis`` instance in tests.

    Args:
        client: Redis-compatible async client.

    Returns:
        None.
    """
    global _redis_client
    _redis_client = client


async def close_redis() -> None:
    """
    Close the Redis connection and reset the singleton.

    Returns:
        None.
    """
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        logger.info("redis_connection_closed")
        _redis_client = None
