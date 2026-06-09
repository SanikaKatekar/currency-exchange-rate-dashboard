"""
Pydantic schemas for public API responses.

Overview:
    Defines typed response models used by FastAPI route handlers and OpenAPI
    documentation generation.

Classes:
    HealthResponse: Liveness payload for ``/api/v1/health``.
    ReadyResponse: Readiness payload for ``/api/v1/ready``.
    DayRate: Single-day FX rate with optional day-over-day change.
    SummaryTotals: Aggregated totals for a requested date range.
    SummaryResponse: Primary summary payload returned by ``/api/v1/summary``.
    ErrorResponse: Structured error payload for global exception handlers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Liveness payload returned by ``/api/v1/health``.

    Attributes:
        status: Health status string, typically ``"ok"``.
        timestamp: Current server time in UTC.
        version: Application version string from settings.
        uptime_seconds: Seconds since process startup.
    """

    status: str = "ok"
    timestamp: datetime
    version: str
    uptime_seconds: float


class ReadyResponse(BaseModel):
    """
    Readiness payload returned by ``/api/v1/ready``.

    Attributes:
        status: ``"ready"`` or ``"not_ready"``.
        timestamp: Current server time in UTC.
        sample_file_ready: Whether the offline fallback file exists.
    """

    status: str
    timestamp: datetime
    sample_file_ready: bool


class DayRate(BaseModel):
    """
    Single published FX rate for one business day.

    Attributes:
        date: Calendar date of the published rate.
        rate: FX rate value for the quote currency.
        pct_change: Percent change versus the prior published day, if available.
    """

    date: date
    rate: float
    pct_change: float | None = None


class SummaryTotals(BaseModel):
    """
    Aggregated statistics for a requested date range.

    Attributes:
        start_rate: Rate on the first published day in the range.
        end_rate: Rate on the last published day in the range.
        total_pct_change: Percent change from start to end rate.
        mean_rate: Arithmetic mean of all published daily rates.
    """

    start_rate: float
    end_rate: float
    total_pct_change: float | None
    mean_rate: float


class SummaryResponse(BaseModel):
    """
    Primary summary payload consumed by the dashboard and API clients.

    Attributes:
        from_currency: Base currency code (JSON alias ``from``).
        to_currency: Quote currency code (JSON alias ``to``).
        start: Inclusive start date of the requested analysis window.
        end: Inclusive end date of the requested analysis window.
        breakdown: ``"day"`` when daily rows are included, else ``"none"``.
        days: Optional list of daily rows.
        totals: Aggregated totals for the period.
        source: Data provenance label from the FX provider chain.
    """

    from_currency: str = Field(alias="from")
    to_currency: str = Field(alias="to")
    start: date
    end: date
    breakdown: Literal["day", "none"]
    days: list[DayRate] | None = None
    totals: SummaryTotals
    source: str

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """
    Structured error payload returned by global exception handlers.

    Attributes:
        error: Human-readable error message.
        code: Stable machine-readable error code.
        request_id: Correlation ID for the failing request.
    """

    error: str
    code: str
    request_id: str
