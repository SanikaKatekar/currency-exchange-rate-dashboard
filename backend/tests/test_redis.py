"""
Redis-backed resilience tests using fakeredis.

Overview:
    Validates shared cache transparency, sliding-window rate limits, and the
    circuit breaker finite state machine without a live Redis server.
"""

from __future__ import annotations

import time
from datetime import date

import pytest

from app.adapters.fx_providers import CachedFxProvider
from app.core.circuit_breaker import CircuitState, RedisCircuitBreaker
from app.core.rate_limiter import allow_request
from app.domain.ports import FxSeries


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess_requests() -> None:
    """Reject requests once the per-minute sliding window is full."""
    client_ip = "203.0.113.10"
    limit = 5
    for _ in range(limit):
        assert await allow_request(client_ip, limit) is True
    assert await allow_request(client_ip, limit) is False


@pytest.mark.asyncio
async def test_rate_limit_isolated_per_ip() -> None:
    """Track limits independently for different client IPs."""
    limit = 2
    assert await allow_request("10.0.0.1", limit) is True
    assert await allow_request("10.0.0.1", limit) is True
    assert await allow_request("10.0.0.1", limit) is False
    assert await allow_request("10.0.0.2", limit) is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold() -> None:
    """Open the circuit after repeated failures reach the configured threshold."""
    breaker = RedisCircuitBreaker("test-open", failure_threshold=2, cooldown_seconds=30)
    assert await breaker.allow_request() is True
    await breaker.record_failure()
    assert await breaker.allow_request() is True
    await breaker.record_failure()
    assert await breaker.allow_request() is False


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow a probe request after the cooldown elapses."""
    breaker = RedisCircuitBreaker("test-half-open", failure_threshold=1, cooldown_seconds=30)
    await breaker.record_failure()
    assert await breaker.allow_request() is False

    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:test-half-open"
    await redis.set(f"{prefix}:opened_at", time.time() - 31)
    assert await breaker.allow_request() is True
    state = await redis.get(f"{prefix}:state")
    assert state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_to_closed() -> None:
    """Return to the closed state after a successful upstream call."""
    breaker = RedisCircuitBreaker("test-reset", failure_threshold=1, cooldown_seconds=30)
    await breaker.record_failure()
    assert await breaker.allow_request() is False
    await breaker.record_success()
    assert await breaker.allow_request() is True


@pytest.mark.asyncio
async def test_cache_hit_preserves_origin_across_calls() -> None:
    """Return transparent cache labels for repeated identical requests."""
    class StubProvider:
        calls = 0

        async def fetch_rates(
            self,
            start: date,
            end: date,
            from_currency: str,
            to_currency: str,
        ) -> FxSeries:
            StubProvider.calls += 1
            return FxSeries.create({start: 1.2345}, "live")

    provider = CachedFxProvider(StubProvider(), ttl_seconds=120)
    first = await provider.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    second = await provider.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert first.source == "live"
    assert second.source == "cache(live)"
    assert StubProvider.calls == 1
