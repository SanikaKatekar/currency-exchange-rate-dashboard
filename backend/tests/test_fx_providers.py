"""
Integration tests for Frankfurter, cache, and fallback FX providers.

Overview:
    Uses ``respx`` to mock Frankfurter HTTP responses and validates retry,
    cache, and offline fallback behavior in the adapter layer.

Fixtures:
    settings: Temporary settings object with an isolated sample FX file.

Functions:
    test_frankfurter_adapter_success: Live adapter parses v1 range payload.
    test_frankfurter_adapter_retries_then_succeeds: Retry succeeds after 500.
    test_file_fallback_adapter: Offline adapter reads sample file data.
    test_cached_provider_returns_cache_source: Cache prevents duplicate fetches.
    test_fallback_provider_uses_file_when_network_fails: Fallback after outage.
"""

from __future__ import annotations

import json
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
)
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
    return Settings(sample_fx_path=sample, cache_ttl_seconds=60, max_retries=2)


@pytest.mark.asyncio
@respx.mock
async def test_frankfurter_adapter_success(settings: Settings) -> None:
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
        adapter = FrankfurterAdapter(settings, client)
        series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "live"
    assert len(series.rates) == 2


@pytest.mark.asyncio
@respx.mock
async def test_frankfurter_adapter_retries_then_succeeds(settings: Settings) -> None:
    """Retry a failed request and succeed on the next attempt."""
    route = respx.get(
        "https://api.frankfurter.dev/v1/2026-06-03?base=EUR&symbols=USD"
    )
    route.side_effect = [
        Response(500),
        Response(
            200,
            json={"date": "2026-06-03", "rates": {"USD": 1.1614}},
        ),
    ]
    respx.get("https://api.frankfurter.dev/latest?from=EUR&to=USD").mock(
        return_value=Response(404)
    )
    async with httpx.AsyncClient() as client:
        adapter = FrankfurterAdapter(settings, client)
        series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert series.rates[date(2026, 6, 3)] == 1.1614


@pytest.mark.asyncio
async def test_file_fallback_adapter(settings: Settings) -> None:
    """Read offline rates from the configured sample file."""
    adapter = FileFallbackAdapter(settings)
    assert adapter.is_ready() is True
    series = await adapter.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "offline_fallback"


@pytest.mark.asyncio
async def test_cached_provider_returns_cache_source(settings: Settings) -> None:
    """Serve the second identical request from cache."""
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
            return FxSeries(rates={start: 1.1}, source="live")

    inner = StubProvider()
    cached = CachedFxProvider(inner, ttl_seconds=60)
    first = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    second = await cached.fetch_rates(date(2026, 6, 3), date(2026, 6, 3), "EUR", "USD")
    assert first.source == "live"
    assert second.source == "cache"
    assert StubProvider.calls == 1


@pytest.mark.asyncio
@respx.mock
async def test_fallback_provider_uses_file_when_network_fails(settings: Settings) -> None:
    """Use offline fallback when all Frankfurter requests fail."""
    respx.get(url__regex=r"https://api\.frankfurter\.dev/.*").mock(return_value=Response(500))
    async with httpx.AsyncClient() as client:
        primary = FrankfurterAdapter(settings, client)
        fallback = FallbackFxProvider(primary, FileFallbackAdapter(settings))
        series = await fallback.fetch_rates(date(2026, 6, 3), date(2026, 6, 4), "EUR", "USD")
    assert series.source == "offline_fallback"
