from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import DayRate, SummaryResponse, SummaryTotals
from app.services.fx_calculator import build_day_rows, build_totals
from app.services.fx_client import fetch_rates

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/summary", response_model=SummaryResponse)
def summary(
    start: date = Query(..., description="Start date (inclusive), e.g. 2024-07-01"),
    end: date = Query(..., description="End date (inclusive), e.g. 2024-07-03"),
    breakdown: Literal["day", "none"] = Query(
        "day",
        description="Include day-by-day rows or totals only.",
    ),
) -> SummaryResponse:
    try:
        daily_rates, source = fetch_rates(start=start, end=end)
        totals_data = build_totals(daily_rates)
        day_rows = build_day_rows(daily_rates) if breakdown == "day" else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SummaryResponse(
        **{
            "from": "EUR",
            "to": "USD",
            "start": start,
            "end": end,
            "breakdown": breakdown,
            "days": [DayRate(**row) for row in day_rows] if day_rows else None,
            "totals": SummaryTotals(**totals_data),
            "source": source,
        }
    )
