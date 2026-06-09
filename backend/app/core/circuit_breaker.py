"""
Redis-backed circuit breaker with closed, open, and half-open states.

Overview:
    Implements a three-state circuit breaker shared across all API worker
    processes. Half-open allows exactly one probe request via a Redis SETNX lock.

Classes:
    RedisCircuitBreaker: Async circuit breaker backed by Redis keys.
"""

from __future__ import annotations

import time
from enum import StrEnum

from app.core.logging_config import get_logger
from app.core.metrics import CIRCUIT_OPENS
from app.core.redis_client import get_redis

logger = get_logger("circuit_breaker")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open and no probe slot is available."""


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

    async def _try_acquire_probe(self, redis) -> bool:
        """
        Atomically claim the single half-open probe slot.

        Returns:
            ``True`` when this caller acquired the probe lock, else ``False``.
        """
        probe_key = f"{self._prefix}:probe"
        acquired = await redis.set(
            probe_key,
            "1",
            nx=True,
            ex=self._cooldown_seconds,
        )
        if acquired:
            await redis.set(f"{self._prefix}:state", CircuitState.HALF_OPEN)
            return True
        return False

    async def allow_request(self) -> bool:
        """
        Determine whether a request should be allowed through the breaker.

        Returns:
            ``True`` when closed or this caller holds the half-open probe slot;
            ``False`` when open or another caller is probing.
        """
        redis = get_redis()
        state = await redis.get(f"{self._prefix}:state")
        if state is None or state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            probe_key = f"{self._prefix}:probe"
            if await redis.exists(probe_key):
                return False
            return await self._try_acquire_probe(redis)
        if state == CircuitState.OPEN:
            opened_at = float(await redis.get(f"{self._prefix}:opened_at") or 0)
            if time.time() - opened_at < self._cooldown_seconds:
                return False
            return await self._try_acquire_probe(redis)
        return True

    async def record_success(self) -> None:
        """
        Record a successful upstream call and reset the breaker to closed.

        Returns:
            None.
        """
        redis = get_redis()
        await redis.delete(f"{self._prefix}:probe")
        await redis.set(f"{self._prefix}:state", CircuitState.CLOSED)
        await redis.set(f"{self._prefix}:failures", 0)

    async def record_failure(self) -> None:
        """
        Record a failed upstream call and open the circuit when threshold is hit.

        Returns:
            None.
        """
        redis = get_redis()
        await redis.delete(f"{self._prefix}:probe")
        failures = await redis.incr(f"{self._prefix}:failures")
        state = await redis.get(f"{self._prefix}:state")
        if state == CircuitState.HALF_OPEN or failures >= self._failure_threshold:
            await redis.set(f"{self._prefix}:state", CircuitState.OPEN)
            await redis.set(f"{self._prefix}:opened_at", time.time())
            CIRCUIT_OPENS.inc()
            logger.warning(
                "circuit_opened breaker=%s failures=%s state=%s threshold=%s",
                self._prefix,
                failures,
                state,
                self._failure_threshold,
            )
