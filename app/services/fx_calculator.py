from datetime import date


def pct_change(current: float, previous: float | None) -> float | None:
    """Return percent change; None when prior value is missing or zero."""
    if previous is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


def build_day_rows(daily_rates: dict[date, float]) -> list[dict]:
    rows: list[dict] = []
    prior_rate: float | None = None

    for day in sorted(daily_rates):
        rate = daily_rates[day]
        rows.append(
            {
                "date": day,
                "rate": round(rate, 4),
                "pct_change": pct_change(rate, prior_rate),
            }
        )
        prior_rate = rate

    return rows


def build_totals(daily_rates: dict[date, float]) -> dict:
    if not daily_rates:
        raise ValueError("No rates available for the requested range.")

    ordered = [daily_rates[d] for d in sorted(daily_rates)]
    start_rate = ordered[0]
    end_rate = ordered[-1]
    mean_rate = sum(ordered) / len(ordered)

    return {
        "start_rate": round(start_rate, 4),
        "end_rate": round(end_rate, 4),
        "total_pct_change": pct_change(end_rate, start_rate),
        "mean_rate": round(mean_rate, 4),
    }
