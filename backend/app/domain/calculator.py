"""
Pure business logic for FX percentage changes and summary totals.

Overview:
    Contains domain calculations with no HTTP or external I/O dependencies.
    Used by the summary service to build day rows and period totals.

Functions:
    pct_change: Compute percent change between two rates with zero-safe behavior.
    build_day_rows: Build ordered daily rows including day-over-day changes.
    build_totals: Compute start/end/mean rates and total percent change.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import TypedDict


class DayRow(TypedDict):
    """Dictionary shape for a single daily FX summary row."""

    date: date
    rate: float
    pct_change: float | None


class SummaryTotalsDict(TypedDict):
    """Dictionary shape for aggregated FX totals."""

    start_rate: float
    end_rate: float
    total_pct_change: float | None
    mean_rate: float


def pct_change(current: float, previous: float | None) -> float | None:
    """
    Calculate percent change between two FX rates.

    Returns ``None`` when the previous value is missing or zero to avoid division
    by zero and to indicate that no prior comparison exists.

    Args:
        current: Current rate value.
        previous: Prior rate value, or ``None`` when unavailable.

    Returns:
        Percent change rounded to two decimal places, or ``None`` when undefined.
    """
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def build_day_rows(daily_rates: Mapping[date, float]) -> list[DayRow]:
    """
    Build ordered daily rows with day-over-day percentage changes.

    Args:
        daily_rates: Mapping of calendar dates to FX rates.

    Returns:
        List of row dictionaries sorted by date ascending. The first row always
        has ``pct_change=None``.
    """
    rows: list[DayRow] = []
    prior_rate: float | None = None

    for day in sorted(daily_rates):
        rate: float = daily_rates[day]
        rows.append(
            {
                "date": day,
                "rate": round(rate, 4),
                "pct_change": pct_change(rate, prior_rate),
            }
        )
        prior_rate = rate

    return rows


def build_totals(daily_rates: Mapping[date, float]) -> SummaryTotalsDict:
    """
    Compute headline totals for the selected date range.

    Args:
        daily_rates: Mapping of calendar dates to FX rates.

    Returns:
        Dictionary containing ``start_rate``, ``end_rate``, ``total_pct_change``,
        and ``mean_rate``.

    Raises:
        ValueError: If ``daily_rates`` is empty.
    """
    if not daily_rates:
        raise ValueError("No rates available for the requested range.")

    ordered: list[float] = [daily_rates[d] for d in sorted(daily_rates)]
    start_rate: float = ordered[0]
    end_rate: float = ordered[-1]
    mean_rate: float = sum(ordered) / len(ordered)

    return {
        "start_rate": round(start_rate, 4),
        "end_rate": round(end_rate, 4),
        "total_pct_change": pct_change(end_rate, start_rate),
        "mean_rate": round(mean_rate, 4),
    }
