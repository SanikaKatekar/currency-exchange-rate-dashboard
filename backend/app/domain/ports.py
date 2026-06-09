"""
Domain contracts for FX rate retrieval.

Overview:
    Defines the core domain models and the provider port used by adapters to
    supply FX time series data to the summary service.

Classes:
    FxSeries: Immutable container for daily rates and data source metadata.
    FxRateProvider: Protocol describing async FX rate retrieval behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class FxSeries:
    """
    Normalized daily FX rates plus provenance metadata.

    Attributes:
        rates: Mapping of calendar dates to FX rates for the quote currency.
        source: Data provenance label (for example ``live``, ``cache``,
            ``offline_fallback``).
    """

    rates: dict[date, float]
    source: str


class FxRateProvider(Protocol):
    """
    Port implemented by live, cached, and fallback FX adapters.

    Methods:
        fetch_rates: Retrieve FX rates for a date range and currency pair.
    """

    async def fetch_rates(
        self,
        start: date,
        end: date,
        from_currency: str,
        to_currency: str,
    ) -> FxSeries:
        """
        Retrieve FX rates for the requested date range.

        Args:
            start: Inclusive start date of the requested range.
            end: Inclusive end date of the requested range.
            from_currency: Base currency ISO code (for example ``EUR``).
            to_currency: Quote currency ISO code (for example ``USD``).

        Returns:
            ``FxSeries`` containing filtered daily rates and a source label.
        """
