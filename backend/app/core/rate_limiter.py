"""
Redis-backed sliding-window rate limiter.

Overview:
    Enforces per-client request limits shared across all API worker processes
    using an atomic Lua script over a sorted-set sliding window.

Functions:
    allow_request: Return whether a client is within the configured limit.
"""

from __future__ import annotations

import time
import uuid

from app.core.redis_client import get_redis

# Atomic check-then-add. Prunes expired entries, counts, and only adds the new
# entry if the request is accepted. Rejected requests never enter the window,
# so rate-limited clients recover cleanly after the window expires.
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local count = redis.call('ZCARD', key)
if count >= limit then
    return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, 60)
return 1
"""


async def allow_request(client_id: str, limit_per_minute: int) -> bool:
    """
    Check whether a client is within the sliding-window rate limit.

    Args:
        client_id: Client identifier (IP address or API key name).
        limit_per_minute: Maximum allowed requests in a 60-second window.

    Returns:
        True if the request is allowed, False if the limit is exceeded.
    """
    redis = get_redis()
    key = f"fx:ratelimit:{client_id}"
    now = time.time()
    window_start = now - 60
    member = f"{now}:{uuid.uuid4().hex}"

    result = await redis.eval(
        _RATE_LIMIT_SCRIPT,
        1,
        key,
        str(now),
        str(window_start),
        str(limit_per_minute),
        member,
    )
    return bool(int(result))
