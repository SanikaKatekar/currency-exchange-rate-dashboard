"""
Shared pytest fixtures for backend integration tests.

Overview:
    Injects a ``fakeredis`` client so cache, rate limiting, and circuit breaker
    tests run without a live Redis server. Provides a ``configured_api_key``
    fixture for tests that exercise the authenticated summary endpoints.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.core.redis_client import close_redis, set_redis_client


@pytest.fixture
def configured_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """
    Configure a known API key and reset cached settings.

    Sets ``API_KEYS`` in the environment and clears the ``get_settings`` cache
    so subsequent calls return settings with the test key configured.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment overrides.

    Returns:
        The raw API key string that was configured.
    """
    key = "test-key-abc123"
    monkeypatch.setenv("API_KEYS", f"test-client:{key}")
    from app.core.settings import get_settings

    get_settings.cache_clear()
    yield key
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
async def fake_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """
    Provide an isolated in-memory Redis instance for every test.

    Patches ``init_redis`` so ASGI lifespan hooks also use fakeredis.
    """
    import fakeredis.aioredis

    client = fakeredis.aioredis.FakeRedis(decode_responses=True)

    async def _init_redis(_url: str) -> None:
        set_redis_client(client)

    # Patch both the module and main's imported binding so lifespan uses fakeredis.
    monkeypatch.setattr("app.core.redis_client.init_redis", _init_redis)
    monkeypatch.setattr("app.main.init_redis", _init_redis)
    set_redis_client(client)
    yield
    await close_redis()
