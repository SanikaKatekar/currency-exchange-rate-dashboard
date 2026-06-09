"""
Integration tests for Frankfurter, cache, and fallback FX providers.

Overview:
    Uses ``respx`` to mock Frankfurter HTTP responses and validates retry,
    Redis cache, and offline fallback behavior in the adapter layer.

Fixtures:
    settings: Temporary settings object with an isolated sample FX file.
    breaker: Redis-backed circuit breaker for Frankfurter adapter tests.

Functions:
    test_frankfurter_adapter_success: Live adapter parses v1 range payload.
    test_frankfurter_adapter_retries_then_succeeds: Same URL retried until success.
    test_file_fallback_adapter: Offline adapter reads sample file data.
    test_cached_provider_returns_cache_live_source: Cache preserves live origin.
    test_cached_provider_returns_cache_offline_source: Cache preserves offline origin.
    test_fallback_provider_uses_file_when_network_fails: Fallback after outage.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from app.adapters.fx_providers import (
    CachedFxProvider,
    FallbackFxProvider,
    FileFallbackAdapter,
    FrankfurterAdapter,
    cache_source_label,
    parse_rates_payload,
)
from app.core.circuit_breaker import CircuitOpenError, CircuitState, RedisCircuitBreaker
from app.core.settings import Settings
from app.domain.ports import FxSeries


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """
    Build settings pointing at a temporary offline sample file.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        ``Settings`` configured for isolated adapter tests.
    """
    sample = tmp_path / "sample_fx.json"
    sample.write_text(
        json.dumps(
            {
                "rates": {
                    "2026-06-03": {"USD": 1.1614},
                    "2026-06-04": {"USD": 1.164},
                }
            }
        ),
        encoding="utf-8",
    )
    return Settings(
        sample_fx_path=sample,
        cache_ttl_seconds=60,
        max_retries=3,
        circuit_breaker_cooldown_seconds=30,
    )


@pytest.fixture
def breaker(settings: Settings) -> RedisCircuitBreaker:
    """Return a Redis-backed circuit breaker for adapter tests."""
    return RedisCircuitBreaker(
        "frankfurter",
        settings.circuit_breaker_threshold,
        settings.circuit_breaker_cooldown_seconds,
    )


def test_cache_source_label_maps_origin_transparently() -> None:
    """Map stored cache origins to user-visible source labels."""
    assert cache_source_label("offline_fallback") == "cache(offline)"
    assert cache_source_label("live") == "cache(live)"


def test_parse_rates_payload_single_day() -> None:
    """Parse Frankfurter single-day payloads with a top-level date field."""
    daily = parse_rates_payload(
        {"date": "2026-06-03", "rates": {"USD": 1.1614}},
        "USD",
    )
    assert daily[date(2026, 6, 3)] == 1.1614


def test_parse_rates_payload_empty_raises() -> None:
    """Reject payloads that do not include any rates."""
    with pytest.raises(ValueError, match="did not include any rates"):
        parse_rates_payload({"rates": {}}, "USD")


def test_fx_series_create_is_immutable() -> None:
    """Prevent silent mutation of frozen FX series objects."""
    series = FxSeries.create({date(2026, 6, 3): 1.1}, "live")
    with pytest.raises(TypeError):
        series.rates[date(2026, 6, 3)] = 1.2  # type: ignore[index]


@pytest.mark.asyncio
@respx.mock
async def test_frankfurter_adapter_success(
    settings: Settings, breaker: RedisCircuitBreaker
) -> None:
    """Parse a successful Frankfurter v1 range response."""
    respx.get("https://api.frankfurter.dev/2026-06-03..2026-06-04").mock(
        return_value=Response(404)
    )
    respx.get(
        "https://api.frankfurter.dev/v1/2026-06-03..2026-06-04?base=EUR&symbols=USD"
    ).mock(
        return_value=Response(
            200,
            json={
                "rates": {
                    "2026-06-03": {"USD": 1.1614},
                    "2026-06-04": {"USD": 1.164},
                }
            },
        )
    )
    async with httpx.AsyncClient() as client:
        adapter = FrankfurterAdapter(settings, client, breaker)
        series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "live"
    assert len(series.rates) == 2


@pytest.mark.asyncio
@respx.mock
async def test_frankfurter_adapter_retries_then_succeeds(
    settings: Settings, breaker: RedisCircuitBreaker
) -> None:
    """Retry the same URL twice on 500 responses, then succeed on the third attempt."""
    route = respx.get("https://api.frankfurter.dev/latest?from=EUR&to=USD")
    route.side_effect = [
        Response(500),
        Response(500),
        Response(
            200,
            json={"date": "2026-06-03", "rates": {"USD": 1.1614}},
        ),
    ]
    respx.get("https://api.frankfurter.dev/v1/2026-06-03?base=EUR&symbols=USD").mock(
        return_value=Response(404)
    )
    async with httpx.AsyncClient() as client:
        adapter = FrankfurterAdapter(settings, client, breaker)
        series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert series.rates[date(2026, 6, 3)] == 1.1614
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_frankfurter_adapter_open_breaker_makes_no_http_calls(
    settings: Settings, breaker: RedisCircuitBreaker
) -> None:
    """Short-circuit before the URL loop when the circuit breaker is open."""
    from app.core.redis_client import get_redis

    redis = get_redis()
    prefix = "fx:circuit:frankfurter"
    await redis.set(f"{prefix}:state", CircuitState.OPEN)
    await redis.set(f"{prefix}:opened_at", time.time())

    route = respx.get(url__regex=r"https://api\.frankfurter\.dev/.*")
    async with httpx.AsyncClient() as client:
        adapter = FrankfurterAdapter(settings, client, breaker)
        with pytest.raises(CircuitOpenError):
            await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert route.call_count == 0


@pytest.mark.asyncio
async def test_file_fallback_adapter(settings: Settings) -> None:
    """Read offline rates from the configured sample file."""
    adapter = FileFallbackAdapter(settings)
    assert adapter.is_ready() is True
    series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "offline_fallback"


@pytest.mark.asyncio
async def test_cached_provider_returns_cache_live_source(settings: Settings) -> None:
    """Serve the second identical live request from cache with a transparent label."""
    class StubProvider:
        calls: int = 0

        async def fetch_rates(
            self,
            start: date,
            end: date,
            from_currency: str,
            to_currency: str,
        ) -> FxSeries:
            StubProvider.calls += 1
            return FxSeries.create({start: 1.1}, "live")

    inner = StubProvider()
    cached = CachedFxProvider(inner, ttl_seconds=60)
    first = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    second = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert first.source == "live"
    assert second.source == "cache(live)"
    assert StubProvider.calls == 1


@pytest.mark.asyncio
async def test_cached_provider_returns_cache_offline_source(settings: Settings) -> None:
    """Preserve offline origin when serving cached fallback data."""
    class StubProvider:
        calls: int = 0

        async def fetch_rates(
            self,
            start: date,
            end: date,
            from_currency: str,
            to_currency: str,
        ) -> FxSeries:
            StubProvider.calls += 1
            return FxSeries.create({start: 1.1}, "offline_fallback")

    inner = StubProvider()
    cached = CachedFxProvider(inner, ttl_seconds=60)
    first = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    second = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert first.source == "offline_fallback"
    assert second.source == "cache(offline)"
    assert StubProvider.calls == 1


@pytest.mark.asyncio
async def test_fallback_provider_uses_file_when_circuit_open(
    settings: Settings,
) -> None:
    """Serve offline data when the live provider circuit breaker is open."""
    from app.core.circuit_breaker import CircuitOpenError

    class OpenPrimary:
        async def fetch_rates(
            self,
            start: date,
            end: date,
            from_currency: str,
            to_currency: str,
        ) -> FxSeries:
            raise CircuitOpenError("Circuit breaker is open")

    fallback = FallbackFxProvider(OpenPrimary(), FileFallbackAdapter(settings))
    series = await fallback.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "offline_fallback"


@pytest.mark.asyncio
@respx.mock
async def test_fallback_provider_uses_file_when_network_fails(
    settings: Settings, breaker: RedisCircuitBreaker
) -> None:
    """Use offline fallback when all Frankfurter requests fail."""
    respx.get(url__regex=r"https://api\.frankfurter\.dev/.*").mock(return_value=Response(500))
    async with httpx.AsyncClient() as client:
        primary = FrankfurterAdapter(settings, client, breaker)
        fallback = FallbackFxProvider(primary, FileFallbackAdapter(settings))
        series = await fallback.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "offline_fallback"
