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

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Protocol


@dataclass(frozen=True)
class FxSeries:
    """
    Immutable daily FX rates plus provenance metadata.

    Attributes:
        rates: Read-only mapping of calendar dates to FX rates.
        source: Data provenance label (live, cache(live), cache(offline), etc.).

    Methods:
        create: Build an immutable ``FxSeries`` from a mutable rates dictionary.
    """

    rates: Mapping[date, float]
    source: str

    @staticmethod
    def create(rates: dict[date, float], source: str) -> FxSeries:
        """
        Build an immutable ``FxSeries`` from a mutable rates dictionary.

        Args:
            rates: Daily FX rates keyed by calendar date.
            source: Provenance label describing where the data originated.

        Returns:
            Frozen ``FxSeries`` with a read-only rates mapping.
        """
        return FxSeries(rates=MappingProxyType(dict(rates)), source=source)


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
