"""
Redis-backed circuit breaker with closed, open, and half-open states.

Overview:
    Implements a three-state circuit breaker shared across all API worker
    processes. Protects upstream Frankfurter calls from repeated failures.

Classes:
    RedisCircuitBreaker: Async circuit breaker backed by Redis keys.
"""

from __future__ import annotations

import time
from enum import StrEnum

from app.core.metrics import CIRCUIT_OPENS
from app.core.redis_client import get_redis


class CircuitState(StrEnum):
    """Valid circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RedisCircuitBreaker:
    """
    Redis-backed circuit breaker with closed/open/half-open recovery.

    Methods:
        allow_request: Decide whether an upstream call may proceed.
        record_success: Reset breaker to closed after a successful call.
        record_failure: Increment failures and open the circuit when needed.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int,
        cooldown_seconds: int,
    ) -> None:
        """
        Initialize breaker namespaced keys in Redis.

        Args:
            name: Logical breaker name (for example ``frankfurter``).
            failure_threshold: Failures required to open the circuit.
            cooldown_seconds: Seconds to remain open before half-open probe.
        """
        self._prefix = f"fx:circuit:{name}"
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds

    async def allow_request(self) -> bool:
        """
        Determine whether a request should be allowed through the breaker.

        Returns:
            ``True`` when the breaker is closed or half-open; ``False`` when open.
        """
        redis = get_redis()
        state = await redis.get(f"{self._prefix}:state")
        if state is None or state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        if state == CircuitState.OPEN:
            opened_at = float(await redis.get(f"{self._prefix}:opened_at") or 0)
            if time.time() - opened_at >= self._cooldown_seconds:
                await redis.set(f"{self._prefix}:state", CircuitState.HALF_OPEN)
                return True
            return False
        return True

    async def record_success(self) -> None:
        """
        Record a successful upstream call and reset the breaker to closed.

        Returns:
            None.
        """
        redis = get_redis()
        await redis.set(f"{self._prefix}:state", CircuitState.CLOSED)
        await redis.set(f"{self._prefix}:failures", 0)

    async def record_failure(self) -> None:
        """
        Record a failed upstream call and open the circuit when threshold is hit.

        Returns:
            None.
        """
        redis = get_redis()
        failures = await redis.incr(f"{self._prefix}:failures")
        state = await redis.get(f"{self._prefix}:state")
        if state == CircuitState.HALF_OPEN or failures >= self._failure_threshold:
            await redis.set(f"{self._prefix}:state", CircuitState.OPEN)
            await redis.set(f"{self._prefix}:opened_at", time.time())
            CIRCUIT_OPENS.inc()
