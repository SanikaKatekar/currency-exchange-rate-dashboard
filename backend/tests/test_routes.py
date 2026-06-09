"""
API route tests for health, readiness, and summary endpoints.

Overview:
    Exercises FastAPI routes through ASGI transport with isolated sample file
    configuration for readiness checks.

Fixtures:
    sample_file: Temporary sample FX file and dependency cache reset.

Functions:
    test_health_has_timestamp: Health response includes timestamp metadata.
    test_ready_ok: Ready endpoint succeeds when Redis and sample file are healthy.
    test_summary_validation_error: Invalid date range returns HTTP 400.
    test_summary_happy_path: Summary math matches mocked Frankfurter data.
    test_openapi_contains_summary: OpenAPI schema exposes summary route.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app.main import app


@pytest.fixture
def sample_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    Point settings at a temporary sample file and reset cached dependencies.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture for environment overrides.

    Returns:
        Path to the created temporary sample FX JSON file.
    """
    sample = tmp_path / "sample_fx.json"
    sample.write_text(
        json.dumps({"rates": {"2026-06-03": {"USD": 1.1614}}}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SAMPLE_FX_PATH", str(sample))
    from app.core.settings import get_settings

    get_settings.cache_clear()
    from app.api.v1 import dependencies as deps

    deps._summary_service = None
    deps._file_adapter = None
    yield sample
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health_has_timestamp() -> None:
    """Health endpoint returns status, timestamp, version, and uptime."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "timestamp" in payload
    assert "version" in payload
    assert "uptime_seconds" in payload


@pytest.mark.asyncio
async def test_ready_ok(sample_file: Path) -> None:
    """Ready endpoint returns 200 when Redis and the sample fallback file are healthy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_file_ready"] is True
    assert payload["redis_ready"] is True


@pytest.mark.asyncio
async def test_ready_returns_503_when_redis_unavailable(
    sample_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ready endpoint returns 503 when Redis is unreachable."""

    async def _redis_down() -> bool:
        return False

    monkeypatch.setattr("app.api.v1.routes.ping_redis", _redis_down)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 503
    payload = response.json()["detail"]
    assert payload["sample_file_ready"] is True
    assert payload["redis_ready"] is False


@pytest.mark.asyncio
async def test_summary_validation_error() -> None:
    """Invalid date range returns HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/summary",
            params={"start": "2026-06-09", "end": "2026-06-03", "breakdown": "day"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
@respx.mock
async def test_summary_happy_path(sample_file: Path) -> None:
    """Return correct totals and daily rows for mocked Frankfurter data."""
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
                    "2026-06-03": {"USD": 1.0},
                    "2026-06-04": {"USD": 1.1},
                }
            },
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/summary",
            params={"start": "2026-06-03", "end": "2026-06-04", "breakdown": "day"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "live"
    assert payload["totals"]["start_rate"] == 1.0
    assert payload["totals"]["end_rate"] == 1.1
    assert payload["totals"]["mean_rate"] == pytest.approx(1.05)
    assert payload["totals"]["total_pct_change"] == pytest.approx(10.0)
    assert len(payload["days"]) == 2
    assert payload["days"][0]["pct_change"] is None
    assert payload["days"][1]["pct_change"] == pytest.approx(10.0)


@pytest.mark.asyncio
@respx.mock
async def test_summary_breakdown_none(sample_file: Path) -> None:
    """Return totals only when breakdown is set to none."""
    respx.get("https://api.frankfurter.dev/latest?from=EUR&to=USD").mock(
        return_value=Response(404)
    )
    respx.get(
        "https://api.frankfurter.dev/v1/2026-06-03?base=EUR&symbols=USD"
    ).mock(
        return_value=Response(
            200,
            json={"date": "2026-06-03", "rates": {"USD": 1.1614}},
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/summary",
            params={"start": "2026-06-03", "end": "2026-06-03", "breakdown": "none"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["days"] is None
    assert payload["totals"]["start_rate"] == 1.1614


@pytest.mark.asyncio
@respx.mock
async def test_legacy_summary_route(sample_file: Path) -> None:
    """Legacy unversioned summary route returns the same payload shape."""
    respx.get(url__regex=r"https://api\.frankfurter\.dev/.*").mock(
        return_value=Response(
            200,
            json={"date": "2026-06-03", "rates": {"USD": 1.1614}},
        )
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/summary",
            params={"start": "2026-06-03", "end": "2026-06-03", "breakdown": "day"},
        )
    assert response.status_code == 200
    assert response.json()["source"] in {"live", "cache(live)"}


@pytest.mark.asyncio
async def test_summary_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """Return HTTP 429 when the Redis-backed per-IP limit is exceeded."""
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    from app.api.v1 import dependencies as deps
    from app.core.settings import get_settings

    get_settings.cache_clear()
    deps._summary_service = None

    transport = ASGITransport(app=app)
    params = {"start": "2026-06-03", "end": "2026-06-04", "breakdown": "day"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/v1/summary", params=params)
        response = await client.get("/api/v1/summary", params=params)
    assert response.status_code == 429
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_summary_date_range_too_large() -> None:
    """Reject date ranges longer than one year with HTTP 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/summary",
            params={"start": "2024-01-01", "end": "2026-06-09", "breakdown": "day"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_legacy_health_endpoint() -> None:
    """Legacy health route remains available for older clients."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_503_without_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ready endpoint returns 503 when the offline sample file is missing."""
    monkeypatch.setenv("SAMPLE_FX_PATH", "/tmp/missing-sample-fx.json")
    from app.api.v1 import dependencies as deps
    from app.core.settings import get_settings

    get_settings.cache_clear()
    deps._file_adapter = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 503
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_live_alias_matches_health() -> None:
    """Live endpoint mirrors the versioned health payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/api/v1/health")
        live = await client.get("/api/v1/live")
    assert live.status_code == 200
    assert live.json()["status"] == health.json()["status"]


@pytest.mark.asyncio
async def test_openapi_contains_summary() -> None:
    """OpenAPI schema includes the versioned summary route."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/summary" in schema["paths"]
