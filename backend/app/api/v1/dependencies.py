"""
Dependency injection helpers for API routes and application lifespan.

Overview:
    Provides singleton accessors for shared HTTP clients, FX provider chains,
    summary services, and process uptime tracking used by route handlers.

Functions:
    set_start_time: Record process start time for uptime reporting.
    get_start_time: Read process start time with a safe default.
    get_http_client: Return the shared async HTTP client.
    get_file_adapter: Return the singleton offline fallback adapter.
    get_summary_service: Build or return the cached summary service chain.
    close_http_client: Close shared clients and reset singletons on shutdown.
"""

from __future__ import annotations

import time

import httpx

from app.adapters.fx_providers import (
    CachedFxProvider,
    FallbackFxProvider,
    FileFallbackAdapter,
    FrankfurterAdapter,
)
from app.core.circuit_breaker import RedisCircuitBreaker
from app.core.settings import Settings, get_settings
from app.domain.service import SummaryService

HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=8.0, write=5.0, pool=3.0)

_http_client: httpx.AsyncClient | None = None
_summary_service: SummaryService | None = None
_file_adapter: FileFallbackAdapter | None = None
_start_time: float | None = None


def set_start_time(value: float) -> None:
    """
    Record process start time for uptime reporting.

    Args:
        value: Unix timestamp captured at application startup.

    Returns:
        None.
    """
    global _start_time
    _start_time = value


def get_start_time() -> float:
    """
    Return process start time, defaulting to ``time.time()`` if unset.

    Returns:
        Unix timestamp representing when the process started, or the current
        time if startup hooks have not yet executed.
    """
    return _start_time if _start_time is not None else time.time()


def get_http_client() -> httpx.AsyncClient:
    """
    Return the shared async HTTP client used for Frankfurter requests.

    Returns:
        Singleton ``httpx.AsyncClient`` instance, created lazily on first use.
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT)
    return _http_client


def get_file_adapter(settings: Settings | None = None) -> FileFallbackAdapter:
    """
    Return the singleton offline fallback adapter.

    Args:
        settings: Optional settings override. When omitted, ``get_settings()``
            is used.

    Returns:
        Shared ``FileFallbackAdapter`` instance.
    """
    global _file_adapter
    if _file_adapter is None:
        _file_adapter = FileFallbackAdapter(settings or get_settings())
    return _file_adapter


def get_summary_service(settings: Settings | None = None) -> SummaryService:
    """
    Build or return the cached summary service with the full provider chain.

    Provider chain order:
        FrankfurterAdapter -> FallbackFxProvider -> CachedFxProvider -> SummaryService

    Args:
        settings: Optional settings override. When omitted, ``get_settings()``
            is used.

    Returns:
        Shared ``SummaryService`` wired to the resilient FX provider stack.
    """
    global _summary_service
    if _summary_service is None:
        settings = settings or get_settings()
        client = get_http_client()
        breaker = RedisCircuitBreaker(
            "frankfurter",
            settings.circuit_breaker_threshold,
            settings.circuit_breaker_cooldown_seconds,
        )
        frankfurter = FrankfurterAdapter(settings, client, breaker)
        fallback = FallbackFxProvider(frankfurter, get_file_adapter(settings))
        cached = CachedFxProvider(fallback, settings.cache_ttl_seconds)
        _summary_service = SummaryService(cached)
    return _summary_service


async def close_http_client() -> None:
    """
    Close shared clients and reset singletons during app shutdown.

    Returns:
        None.
    """
    global _http_client, _summary_service, _file_adapter
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    _summary_service = None
    _file_adapter = None
