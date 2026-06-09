"""
API route tests for health, readiness, and summary endpoints.

Overview:
    Exercises FastAPI routes through ASGI transport with isolated sample file
    configuration for readiness checks.

Fixtures:
    sample_file: Temporary sample FX file and dependency cache reset.

Functions:
    test_health_has_timestamp: Health response includes timestamp metadata.
    test_ready_ok: Ready endpoint succeeds when sample file exists.
    test_summary_validation_error: Invalid date range returns HTTP 400.
    test_openapi_contains_summary: OpenAPI schema exposes summary route.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

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
    """Ready endpoint returns 200 when the sample fallback file exists."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["sample_file_ready"] is True


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
async def test_openapi_contains_summary() -> None:
    """OpenAPI schema includes the versioned summary route."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/summary" in schema["paths"]
