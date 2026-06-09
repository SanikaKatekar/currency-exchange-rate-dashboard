"""
Redis-backed sliding-window rate limiter.

Overview:
    Enforces per-IP request limits shared across all API worker processes.

Functions:
    allow_request: Return whether a client IP is within the configured limit.
"""

from __future__ import annotations

import time

from app.core.redis_client import get_redis


async def allow_request(client_ip: str, limit_per_minute: int) -> bool:
    """
    Check whether a client IP is within the sliding-window rate limit.

    Args:
        client_ip: Client IP address or identifier.
        limit_per_minute: Maximum allowed requests in a 60-second window.

    Returns:
        ``True`` if the request is allowed, ``False`` if the limit is exceeded.
    """
    redis = get_redis()
    key = f"fx:ratelimit:{client_ip}"
    now = time.time()
    window_start = now - 60

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, 60)
    _, _, count, _ = await pipe.execute()
    return int(count) <= limit_per_minute
