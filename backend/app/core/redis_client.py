"""
Shared async Redis client lifecycle management.

Overview:
    Provides a process-wide Redis connection used by cache, rate limiting, and
    circuit breaker modules. Supports test injection via ``set_redis_client``.

Functions:
    init_redis: Connect to Redis using the configured URL.
    get_redis: Return the active Redis client.
    set_redis_client: Inject a Redis client (used by tests with fakeredis).
    close_redis: Close the connection during application shutdown.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

_redis_client: Redis | None = None


async def init_redis(redis_url: str) -> None:
    """
    Connect to Redis and store the client for later use.

    Args:
        redis_url: Redis connection URL (for example ``redis://localhost:6379/0``).

    Returns:
        None.
    """
    from redis.asyncio import from_url

    global _redis_client
    _redis_client = from_url(redis_url, decode_responses=True)  # type: ignore[no-untyped-call]


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
        _redis_client = None
