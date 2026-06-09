"""
Domain service orchestrating FX retrieval and summary assembly.

Overview:
    Coordinates calls to an injected ``FxRateProvider`` and applies domain
    calculations to produce API-ready summary payloads.

Classes:
    SummaryService: Validates input ranges and assembles summary responses.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from app.domain.calculator import DayRow, SummaryTotalsDict, build_day_rows, build_totals
from app.domain.ports import FxRateProvider


class SummaryPayload(dict[str, Any]):
    """Type alias marker for summary service return payloads."""


class SummaryService:
    """
    Coordinates provider calls and summary calculations.

    Methods:
        __init__: Inject the FX provider used to fetch daily rates.
        get_summary: Build a complete summary payload for a date range.
    """

    def __init__(self, provider: FxRateProvider) -> None:
        """
        Create a summary service backed by the given FX provider.

        Args:
            provider: Implementation of ``FxRateProvider`` (live, cached, fallback).
        """
        self._provider: FxRateProvider = provider

    async def get_summary(
        self,
        start: date,
        end: date,
        breakdown: Literal["day", "none"],
        from_currency: str,
        to_currency: str,
    ) -> dict[str, Any]:
        """
        Return an API-ready summary payload for the requested date range.

        Args:
            start: Inclusive start date of the analysis window.
            end: Inclusive end date of the analysis window.
            breakdown: ``"day"`` to include daily rows, or ``"none"`` for totals only.
            from_currency: Base currency ISO code.
            to_currency: Quote currency ISO code.

        Returns:
            Dictionary containing currency pair metadata, optional daily rows,
            totals, and the upstream data ``source`` label.

        Raises:
            ValueError: If the date range is invalid or exceeds one year.
        """
        if end < start:
            raise ValueError("End date must be on or after start date.")
        if (end - start).days > 366:
            raise ValueError("Date range cannot exceed one year.")

        series = await self._provider.fetch_rates(start, end, from_currency, to_currency)
        totals: SummaryTotalsDict = build_totals(series.rates)
        days: list[DayRow] | None = build_day_rows(series.rates) if breakdown == "day" else None

        return {
            "from": from_currency,
            "to": to_currency,
            "start": start,
            "end": end,
            "breakdown": breakdown,
            "days": days,
            "totals": totals,
            "source": series.source,
        }
