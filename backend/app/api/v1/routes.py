"""
Versioned HTTP routes for health checks and FX summaries.

Overview:
    Exposes the public FX Pulse API under ``/api/v1`` plus legacy-compatible
    routes for older clients. Delegates business logic to ``SummaryService``.

Routers:
    router: Versioned ``/api/v1`` routes included in OpenAPI docs.
    legacy_router: Backward-compatible unversioned routes.

Functions:
    health: Return liveness information with timestamp and uptime.
    live: Alias liveness endpoint for orchestrators expecting ``/live``.
    ready: Return readiness based on offline fallback availability.
    _summary_handler: Shared summary logic for versioned and legacy routes.
    summary_v1: Versioned summary endpoint.
    legacy_health: Legacy health endpoint returning only status.
    legacy_summary: Legacy summary endpoint hidden from OpenAPI schema.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.dependencies import get_file_adapter, get_start_time, get_summary_service
from app.api.v1.schemas import (
    DayRate,
    HealthResponse,
    ReadyResponse,
    SummaryResponse,
    SummaryTotals,
)
from app.core.settings import get_settings

router: APIRouter = APIRouter(prefix="/api/v1", tags=["v1"])
legacy_router: APIRouter = APIRouter(tags=["legacy"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Return liveness information including an ISO-8601 timestamp.

    Returns:
        ``HealthResponse`` containing status, timestamp, version, and uptime.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC),
        version=settings.app_version,
        uptime_seconds=round(time.time() - get_start_time(), 2),
    )


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    """
    Alias liveness endpoint for orchestrators expecting ``/live``.

    Returns:
        Same payload as :func:`health`.
    """
    return await health()


@router.get("/ready", response_model=ReadyResponse)
async def ready() -> ReadyResponse:
    """
    Return readiness based on offline fallback file availability.

    Returns:
        ``ReadyResponse`` when the sample fallback file exists.

    Raises:
        HTTPException: Returns HTTP 503 when the sample fallback file is missing.
    """
    file_adapter = get_file_adapter()
    sample_ready: bool = file_adapter.is_ready()
    status: str = "ready" if sample_ready else "not_ready"
    response = ReadyResponse(
        status=status,
        timestamp=datetime.now(UTC),
        sample_file_ready=sample_ready,
    )
    if not sample_ready:
        raise HTTPException(status_code=503, detail=response.model_dump(mode="json"))
    return response


async def _summary_handler(
    start: date,
    end: date,
    breakdown: Literal["day", "none"],
) -> SummaryResponse:
    """
    Shared summary handler used by versioned and legacy routes.

    Args:
        start: Inclusive start date query parameter.
        end: Inclusive end date query parameter.
        breakdown: Detail level, either ``"day"`` or ``"none"``.

    Returns:
        Validated ``SummaryResponse`` model.

    Raises:
        HTTPException: HTTP 400 for validation errors, HTTP 503 for provider failures.
    """
    settings = get_settings()
    service = get_summary_service(settings)
    try:
        payload = await service.get_summary(
            start=start,
            end=end,
            breakdown=breakdown,
            from_currency=settings.default_from,
            to_currency=settings.default_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    days = payload["days"]
    return SummaryResponse(
        **{
            "from": payload["from"],
            "to": payload["to"],
            "start": payload["start"],
            "end": payload["end"],
            "breakdown": payload["breakdown"],
            "days": [DayRate(**row) for row in days] if days else None,
            "totals": SummaryTotals(**payload["totals"]),
            "source": payload["source"],
        }
    )


@router.get("/summary", response_model=SummaryResponse)
async def summary_v1(
    start: date = Query(..., description="Inclusive start date."),
    end: date = Query(..., description="Inclusive end date."),
    breakdown: Literal["day", "none"] = Query("day", description="Daily detail level."),
) -> SummaryResponse:
    """
    Return EUR→USD summary data for the requested date range.

    Args:
        start: Inclusive start date.
        end: Inclusive end date.
        breakdown: Include daily rows when ``"day"``, totals only when ``"none"``.

    Returns:
        ``SummaryResponse`` containing totals, optional daily rows, and source label.
    """
    return await _summary_handler(start, end, breakdown)


@legacy_router.get("/health")
async def legacy_health() -> dict[str, str]:
    """
    Backward-compatible health endpoint without timestamp metadata.

    Returns:
        Dictionary containing only ``{"status": "ok"}``.
    """
    response = await health()
    return {"status": response.status}


@legacy_router.get("/summary", response_model=SummaryResponse, include_in_schema=False)
async def legacy_summary(
    start: date = Query(...),
    end: date = Query(...),
    breakdown: Literal["day", "none"] = Query("day"),
) -> SummaryResponse:
    """
    Backward-compatible summary endpoint for older clients.

    Args:
        start: Inclusive start date.
        end: Inclusive end date.
        breakdown: Detail level, either ``"day"`` or ``"none"``.

    Returns:
        Same ``SummaryResponse`` payload as :func:`summary_v1`.
    """
    return await _summary_handler(start, end, breakdown)
