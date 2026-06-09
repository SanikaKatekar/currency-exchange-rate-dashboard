"""
External FX data adapters: Frankfurter API, cache, and offline fallback.

Overview:
    Implements the ``FxRateProvider`` port using the Frankfurter public API,
    Redis-backed caching, local sample JSON fallback, and composite fallback logic.
    Includes retry, exponential backoff, and a Redis-backed circuit breaker.

Functions:
    parse_rates_payload: Normalize Frankfurter or sample JSON into daily rates.
    build_urls: Build primary and fallback Frankfurter URLs for a date range.
    cache_source_label: Map stored origin labels to transparent cache source names.

Classes:
    FrankfurterAdapter: Live FX provider using async HTTP with retry logic.
    FileFallbackAdapter: Offline provider reading ``sample_fx.json``.
    CachedFxProvider: Decorator that caches provider responses in Redis.
    FallbackFxProvider: Composite provider that falls back after live failure.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from app.core.circuit_breaker import RedisCircuitBreaker
from app.core.metrics import FALLBACKS, RETRIES
from app.core.redis_client import get_redis
from app.core.settings import Settings
from app.domain.ports import FxRateProvider, FxSeries


def parse_rates_payload(payload: dict[str, Any], to_currency: str) -> dict[date, float]:
    """
    Normalize Frankfurter or sample-file payloads into a date→rate mapping.

    Supports both time-series payloads (``rates[date][currency]``) and single-day
    payloads (``rates[currency]`` with top-level ``date``).

    Args:
        payload: Raw JSON payload from Frankfurter or the offline sample file.
        to_currency: Quote currency code to extract from each rate entry.

    Returns:
        Mapping of calendar dates to floating-point FX rates.

    Raises:
        ValueError: If the payload contains no rates or lacks date information.
    """
    rates_block: dict[str, Any] = payload.get("rates", {})
    daily: dict[date, float] = {}

    if not rates_block:
        raise ValueError("FX payload did not include any rates.")

    first_key: str = next(iter(rates_block))
    if isinstance(rates_block[first_key], dict):
        for day_str, quote_rates in rates_block.items():
            daily[date.fromisoformat(day_str)] = float(quote_rates[to_currency])
    else:
        payload_day: str | None = payload.get("date") or payload.get("start_date")
        if not payload_day:
            raise ValueError("FX payload missing date information.")
        daily[date.fromisoformat(payload_day)] = float(rates_block[to_currency])

    return daily


def build_urls(
    settings: Settings,
    start: date,
    end: date,
    from_currency: str,
    to_currency: str,
) -> list[str]:
    """
    Build primary and fallback Frankfurter URLs for a date range.

    Args:
        settings: Application settings containing the Frankfurter base URL.
        start: Inclusive start date.
        end: Inclusive end date.
        from_currency: Base currency ISO code.
        to_currency: Quote currency ISO code.

    Returns:
        Ordered list of URLs to attempt, starting with legacy-style endpoints
        followed by supported ``/v1/`` endpoints.
    """
    start_str: str = start.isoformat()
    end_str: str = end.isoformat()
    base: str = settings.frankfurter_base

    if start == end:
        return [
            f"{base}/latest?from={from_currency}&to={to_currency}",
            f"{base}/v1/{start_str}?base={from_currency}&symbols={to_currency}",
        ]

    return [
        f"{base}/{start_str}..{end_str}?from={from_currency}&to={to_currency}",
        f"{base}/v1/{start_str}..{end_str}?base={from_currency}&symbols={to_currency}",
    ]


def cache_source_label(origin_source: str) -> str:
    """
    Map a stored origin label to a transparent cache source name.

    Args:
        origin_source: Original provider source stored alongside cached rates.

    Returns:
        ``cache(offline)`` when data came from offline fallback, else ``cache(live)``.
    """
    if origin_source == "offline_fallback":
        return "cache(offline)"
    return "cache(live)"


class FrankfurterAdapter:
    """
    Live FX provider backed by the public Frankfurter API.

    Methods:
        __init__: Store settings, HTTP client, and circuit breaker.
        fetch_rates: Retrieve live rates for a date range.
        _request_with_retry: Perform HTTP GET with retry/backoff protection.
        _async_sleep: Non-blocking sleep helper for retry backoff.
    """

    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        breaker: RedisCircuitBreaker,
    ) -> None:
        """
        Initialize the Frankfurter adapter.

        Args:
            settings: Application settings controlling retry and breaker behavior.
            client: Shared async HTTP client used for outbound requests.
            breaker: Redis-backed circuit breaker shared across workers.
        """
        self._settings: Settings = settings
        self._client: httpx.AsyncClient = client
        self._breaker: RedisCircuitBreaker = breaker

    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        """
        Perform an HTTP GET with retry/backoff and circuit-breaker protection.

        Args:
            url: Fully qualified Frankfurter API URL.

        Returns:
            Parsed JSON response body as a dictionary.

        Raises:
            RuntimeError: If the circuit breaker is open or all retries fail.
        """
        if not await self._breaker.allow_request():
            raise RuntimeError("Circuit breaker is open")

        last_error: Exception | None = None
        for attempt in range(self._settings.max_retries):
            try:
                response = await self._client.get(url)
                if response.status_code == 404:
                    raise httpx.HTTPStatusError(
                        "Not found", request=response.request, response=response
                    )
                response.raise_for_status()
                await self._breaker.record_success()
                payload: dict[str, Any] = response.json()
                return payload
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                last_error = exc
                RETRIES.inc()
                if attempt < self._settings.max_retries - 1:
                    await self._async_sleep(
                        self._settings.retry_backoff_seconds * (2**attempt)
                    )

        await self._breaker.record_failure()
        raise RuntimeError(f"Frankfurter request failed after retries: {last_error}")

    async def _async_sleep(self, seconds: float) -> None:
        """
        Sleep without blocking the event loop.

        Args:
            seconds: Number of seconds to wait asynchronously.

        Returns:
            None.
        """
        await asyncio.sleep(seconds)

    async def fetch_rates(
        self,
        start: date,
        end: date,
        from_currency: str,
        to_currency: str,
    ) -> FxSeries:
        """
        Fetch live rates for the requested business-day range.

        Args:
            start: Inclusive start date.
            end: Inclusive end date.
            from_currency: Base currency ISO code.
            to_currency: Quote currency ISO code.

        Returns:
            ``FxSeries`` with ``source="live"`` and rates filtered to the range.

        Raises:
            RuntimeError: If all candidate URLs fail to return usable data.
        """
        errors: list[str] = []
        for url in build_urls(self._settings, start, end, from_currency, to_currency):
            try:
                payload = await self._request_with_retry(url)
                daily = parse_rates_payload(payload, to_currency)
                daily = {day: rate for day, rate in daily.items() if start <= day <= end}
                if not daily:
                    raise ValueError("No exchange rates returned for the requested range.")
                return FxSeries.create(daily, "live")
            except (
                RuntimeError,
                httpx.HTTPError,
                json.JSONDecodeError,
                ValueError,
            ) as exc:
                errors.append(f"{url} -> {exc}")
        raise RuntimeError("; ".join(errors))


class FileFallbackAdapter:
    """
    Offline FX provider backed by a local JSON sample file.

    Methods:
        __init__: Store settings containing the sample file path.
        is_ready: Check whether the sample file exists.
        fetch_rates: Load and filter rates from the sample file.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the file fallback adapter.

        Args:
            settings: Application settings containing ``sample_fx_path``.
        """
        self._settings: Settings = settings

    def is_ready(self) -> bool:
        """
        Return whether the configured sample file exists on disk.

        Returns:
            ``True`` when ``sample_fx_path`` is a readable file, else ``False``.
        """
        return self._settings.sample_fx_path.is_file()

    async def fetch_rates(
        self,
        start: date,
        end: date,
        from_currency: str,
        to_currency: str,
    ) -> FxSeries:
        """
        Load rates from the local sample file when live data is unavailable.

        Args:
            start: Inclusive start date.
            end: Inclusive end date.
            from_currency: Base currency ISO code. Must match sample pair support.
            to_currency: Quote currency ISO code. Must match sample pair support.

        Returns:
            ``FxSeries`` with ``source="offline_fallback"``.

        Raises:
            ValueError: If the requested pair is unsupported or dates are missing
                from the sample file.
            OSError: If the sample file cannot be read.
        """
        if from_currency != self._settings.default_from or to_currency != self._settings.default_to:
            raise ValueError("Offline sample only supports EUR to USD.")

        with Path(self._settings.sample_fx_path).open(encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)
        daily = parse_rates_payload(payload, to_currency)
        filtered = {day: rate for day, rate in daily.items() if start <= day <= end}
        if not filtered:
            raise ValueError("Offline sample data does not cover requested dates.")
        FALLBACKS.inc()
        return FxSeries.create(filtered, "offline_fallback")


class CachedFxProvider:
    """
    Decorator provider that caches FX series in Redis by date range and pair.

    Methods:
        __init__: Wrap an inner provider with a TTL-backed Redis cache.
        fetch_rates: Return cached data when fresh, otherwise delegate inward.
        _key: Build a deterministic cache key for a request.
    """

    def __init__(self, inner: FxRateProvider, ttl_seconds: int) -> None:
        """
        Initialize the caching decorator.

        Args:
            inner: Provider whose responses should be cached.
            ttl_seconds: Number of seconds cached entries remain valid.
        """
        self._inner: FxRateProvider = inner
        self._ttl: int = ttl_seconds

    def _key(self, start: date, end: date, from_currency: str, to_currency: str) -> str:
        """
        Build a deterministic cache key for a provider request.

        Args:
            start: Inclusive start date.
            end: Inclusive end date.
            from_currency: Base currency ISO code.
            to_currency: Quote currency ISO code.

        Returns:
            Stable string key representing the request parameters.
        """
        return f"fx:cache:{from_currency}:{to_currency}:{start.isoformat()}:{end.isoformat()}"

    async def fetch_rates(
        self,
        start: date,
        end: date,
        from_currency: str,
        to_currency: str,
    ) -> FxSeries:
        """
        Return cached rates when fresh, otherwise delegate to the inner provider.

        Args:
            start: Inclusive start date.
            end: Inclusive end date.
            from_currency: Base currency ISO code.
            to_currency: Quote currency ISO code.

        Returns:
            ``FxSeries`` from cache with ``cache(live)`` or ``cache(offline)``,
            or the inner provider result when the cache misses.
        """
        from app.core.metrics import CACHE_HITS, CACHE_MISSES

        redis = get_redis()
        key: str = self._key(start, end, from_currency, to_currency)
        cached = await redis.get(key)
        if cached:
            CACHE_HITS.inc()
            payload = json.loads(cached)
            rates = {date.fromisoformat(k): float(v) for k, v in payload["rates"].items()}
            return FxSeries.create(rates, cache_source_label(payload["origin_source"]))

        CACHE_MISSES.inc()
        series = await self._inner.fetch_rates(start, end, from_currency, to_currency)
        origin = series.source if series.source in ("live", "offline_fallback") else "live"
        await redis.setex(
            key,
            self._ttl,
            json.dumps(
                {
                    "rates": {d.isoformat(): r for d, r in series.rates.items()},
                    "origin_source": origin,
                }
            ),
        )
        return series


class FallbackFxProvider:
    """
    Composite provider that falls back to local sample data after live failure.

    Methods:
        __init__: Wire primary and fallback providers together.
        fetch_rates: Attempt primary fetch, then fallback on any primary error.
    """

    def __init__(self, primary: FxRateProvider, fallback: FileFallbackAdapter) -> None:
        """
        Initialize the composite fallback provider.

        Args:
            primary: First provider to attempt (typically live Frankfurter data).
            fallback: Secondary offline provider used when primary fails.
        """
        self._primary: FxRateProvider = primary
        self._fallback: FileFallbackAdapter = fallback

    async def fetch_rates(
        self,
        start: date,
        end: date,
        from_currency: str,
        to_currency: str,
    ) -> FxSeries:
        """
        Try the primary provider first, then the offline fallback adapter.

        Args:
            start: Inclusive start date.
            end: Inclusive end date.
            from_currency: Base currency ISO code.
            to_currency: Quote currency ISO code.

        Returns:
            ``FxSeries`` from either the primary or fallback provider.

        Raises:
            RuntimeError: If both primary and fallback providers fail.
        """
        try:
            return await self._primary.fetch_rates(start, end, from_currency, to_currency)
        except (RuntimeError, httpx.HTTPError, json.JSONDecodeError, ValueError) as primary_exc:
            try:
                return await self._fallback.fetch_rates(start, end, from_currency, to_currency)
            except (RuntimeError, ValueError, OSError) as fallback_exc:
                raise RuntimeError(
                    f"Network and offline fallback both failed. primary: {primary_exc}; "
                    f"fallback: {fallback_exc}"
                ) from fallback_exc
