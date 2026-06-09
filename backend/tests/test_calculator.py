"""
Unit tests for FX percentage and totals calculations.

Overview:
    Validates domain calculator behavior including zero-safe percent changes,
    first-day null changes, and aggregated totals.

Functions:
    test_pct_change_null_when_no_prior: Ensure missing prior returns None.
    test_pct_change_null_when_zero_prior: Ensure zero prior returns None.
    test_pct_change_calculates: Validate a simple positive percent change.
    test_build_day_rows_first_day_null_change: First row has null pct_change.
    test_build_totals: Validate start/end/mean/total change totals.
    test_build_totals_empty_raises: Empty input raises ValueError.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.calculator import build_day_rows, build_totals, pct_change


def test_pct_change_null_when_no_prior() -> None:
    """Return None when no prior rate exists for comparison."""
    assert pct_change(1.2, None) is None


def test_pct_change_null_when_zero_prior() -> None:
    """Return None when prior rate is zero to avoid division by zero."""
    assert pct_change(1.2, 0) is None


def test_pct_change_calculates() -> None:
    """Calculate a 10% increase from 1.0 to 1.1."""
    assert pct_change(1.1, 1.0) == 10.0


def test_build_day_rows_first_day_null_change() -> None:
    """First daily row should not include a day-over-day change."""
    rows = build_day_rows({date(2024, 7, 1): 1.0745, date(2024, 7, 2): 1.0729})
    assert rows[0]["pct_change"] is None
    assert rows[1]["pct_change"] == pytest.approx(-0.15, abs=0.01)


def test_build_totals() -> None:
    """Compute expected totals for a two-day rate series."""
    totals = build_totals({date(2024, 7, 1): 1.0, date(2024, 7, 2): 1.1})
    assert totals["start_rate"] == 1.0
    assert totals["end_rate"] == 1.1
    assert totals["total_pct_change"] == 10.0
    assert totals["mean_rate"] == 1.05


def test_build_totals_empty_raises() -> None:
    """Raise ValueError when no daily rates are supplied."""
    with pytest.raises(ValueError):
        build_totals({})
