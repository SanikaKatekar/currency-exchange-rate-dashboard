"""
Shared pytest fixtures for backend integration tests.

Overview:
    Injects a ``fakeredis`` client so cache, rate limiting, and circuit breaker
    tests run without a live Redis server.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from app.core.redis_client import close_redis, set_redis_client


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

    monkeypatch.setattr("app.core.redis_client.init_redis", _init_redis)
    set_redis_client(client)
    yield
    await close_redis()
