from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class DayRate(BaseModel):
    date: date
    rate: float
    pct_change: float | None = Field(
        description="Percent change vs prior day; null when unavailable."
    )


class SummaryTotals(BaseModel):
    start_rate: float
    end_rate: float
    total_pct_change: float | None
    mean_rate: float


class SummaryResponse(BaseModel):
    from_currency: str = Field(alias="from")
    to_currency: str = Field(alias="to")
    start: date
    end: date
    breakdown: Literal["day", "none"]
    days: list[DayRate] | None = None
    totals: SummaryTotals
    source: str = Field(description="live API or offline fallback file")

    model_config = {"populate_by_name": True}


class HealthResponse(BaseModel):
    status: str = "ok"
