"""
Tests for global exception handlers.
"""

from __future__ import annotations

import json

import pytest
from starlette.requests import Request

from app.core.exceptions import AppError, app_error_handler, unhandled_error_handler


def _make_request() -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = "test-request-id"
    return request


@pytest.mark.asyncio
async def test_app_error_handler_returns_structured_json() -> None:
    """Serialize AppError instances into consistent JSON responses."""
    response = await app_error_handler(
        _make_request(),
        AppError("Invalid range", "validation_error", status_code=400),
    )
    assert response.status_code == 400
    payload = json.loads(response.body)
    assert payload["error"] == "Invalid range"
    assert payload["code"] == "validation_error"
    assert payload["request_id"] == "test-request-id"


@pytest.mark.asyncio
async def test_unhandled_error_handler_hides_exception_details() -> None:
    """Return a generic 500 payload for unexpected exceptions."""
    response = await unhandled_error_handler(_make_request(), RuntimeError("secret"))
    assert response.status_code == 500
    payload = json.loads(response.body)
    assert payload["code"] == "internal_error"
    assert payload["request_id"] == "test-request-id"
    assert "secret" not in payload["error"]
