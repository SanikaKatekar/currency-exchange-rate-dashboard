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
async def test_get_redis_raises_when_not_initialized() -> None:
    """Raise a clear error when Redis has not been initialized."""
    from app.core.redis_client import close_redis, get_redis

    await close_redis()
    with pytest.raises(RuntimeError, match="not initialized"):
        get_redis()


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
    """Allow a single probe request after the cooldown elapses."""
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
async def test_circuit_breaker_half_open_allows_only_one_probe() -> None:
    """Reject concurrent callers while a half-open probe is in flight."""
    breaker = RedisCircuitBreaker("test-single-probe", failure_threshold=1, cooldown_seconds=30)
    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:test-single-probe"
    await redis.set(f"{prefix}:state", CircuitState.HALF_OPEN)
    await redis.set(f"{prefix}:probe", "1", ex=30)

    assert await breaker.allow_request() is False


@pytest.mark.asyncio
async def test_rate_limit_burst_respects_limit() -> None:
    """Block immediately once the atomic window reaches the configured limit."""
    client_ip = "198.51.100.42"
    limit = 1
    assert await allow_request(client_ip, limit) is True
    assert await allow_request(client_ip, limit) is False


@pytest.mark.asyncio
async def test_circuit_breaker_success_resets_to_closed() -> None:
    """Return to the closed state after a successful upstream call."""
    breaker = RedisCircuitBreaker("test-reset", failure_threshold=1, cooldown_seconds=30)
    await breaker.record_failure()
    assert await breaker.allow_request() is False
    await breaker.record_success()
    assert await breaker.allow_request() is True


@pytest.mark.asyncio
async def test_circuit_breaker_reacquires_probe_when_lock_expired() -> None:
    """Allow a new probe when half-open but the probe lock has expired."""
    breaker = RedisCircuitBreaker("test-reacquire", failure_threshold=1, cooldown_seconds=30)
    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:test-reacquire"
    await redis.set(f"{prefix}:state", CircuitState.HALF_OPEN)
    assert await breaker.allow_request() is True


@pytest.mark.asyncio
async def test_ping_redis_returns_true_with_fake_redis() -> None:
    """Report Redis as healthy when the client responds to PING."""
    from app.core.redis_client import ping_redis

    assert await ping_redis() is True


@pytest.mark.asyncio
async def test_ping_redis_returns_false_when_client_missing() -> None:
    """Report Redis as unavailable when no client is configured."""
    from app.core.redis_client import close_redis, ping_redis

    await close_redis()
    assert await ping_redis() is False


@pytest.mark.asyncio
async def test_circuit_breaker_failure_from_half_open_reopens() -> None:
    """Re-open the circuit when a half-open probe fails."""
    breaker = RedisCircuitBreaker("test-ho-fail", failure_threshold=5, cooldown_seconds=30)
    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:test-ho-fail"
    await redis.set(f"{prefix}:state", CircuitState.HALF_OPEN)
    await redis.set(f"{prefix}:probe", "1", ex=30)
    await breaker.record_failure()
    assert await redis.get(f"{prefix}:state") == CircuitState.OPEN


@pytest.mark.asyncio
async def test_init_redis_connects_and_pings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initialize Redis and verify startup ping succeeds."""
    import fakeredis.aioredis

    from app.core.redis_client import close_redis, get_redis, init_redis

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("redis.asyncio.from_url", lambda *args, **kwargs: fake)
    await close_redis()
    await init_redis("redis://localhost:6379/0")
    assert await get_redis().ping() is True


@pytest.mark.asyncio
async def test_circuit_breaker_only_one_probe_claim_after_cooldown() -> None:
    """Allow only one caller to claim the probe slot after cooldown expires."""
    breaker = RedisCircuitBreaker("test-claim", failure_threshold=1, cooldown_seconds=30)
    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:test-claim"
    await redis.set(f"{prefix}:state", CircuitState.OPEN)
    await redis.set(f"{prefix}:opened_at", time.time() - 31)

    assert await breaker.allow_request() is True
    assert await breaker.allow_request() is False


@pytest.mark.asyncio
async def test_ping_redis_returns_false_on_ping_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report Redis as unavailable when PING raises an error."""
    from app.core.redis_client import get_redis, ping_redis

    redis = get_redis()

    async def bad_ping() -> bool:
        raise ConnectionError("boom")

    monkeypatch.setattr(redis, "ping", bad_ping)
    assert await ping_redis() is False


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
