"""
Direct middleware tests for Redis-backed rate limiting.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_burst_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return HTTP 429 from middleware when the Redis window is exceeded."""
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    from app.api.v1 import dependencies as deps
    from app.core.settings import get_settings

    get_settings.cache_clear()
    deps._summary_service = None

    transport = ASGITransport(app=app)
    params = {"start": "2026-06-03", "end": "2026-06-03", "breakdown": "none"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/summary", params=params)
        second = await client.get("/api/v1/summary", params=params)

    assert first.status_code in {200, 400, 503}
    assert second.status_code == 429
    get_settings.cache_clear()
