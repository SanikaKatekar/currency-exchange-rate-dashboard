# Currency Exchange Rate Dashboard

Track **EUR → USD** exchange rates over any date range. The app combines a human-friendly dashboard with a small JSON API — so analysts can explore trends visually, and developers can integrate the same data programmatically.

**android-cursor ✅**

## Why this design

| Layer | Role |
| --- | --- |
| **Dashboard (`/`)** | Date pickers, summary cards, trend chart, and daily table — the primary experience for most users |
| **API (`/summary`, `/health`)** | Machine-readable endpoints for scripts, tests, and integrations |
| **FX client** | Calls Frankfurter, retries on failure, caches responses, falls back to local sample data |
| **Calculator** | Computes day-over-day `%` change and period totals without duplicating logic in the UI |

Users land on a familiar pattern: pick a range → click **Analyze rates** → read the headline numbers, then drill into the chart and table. No API keys, no setup beyond `pip install`.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) for the dashboard.

## API examples

### Health check

```bash
curl http://localhost:8000/health
```

```json
{ "status": "ok" }
```

### Daily breakdown

```bash
curl "http://localhost:8000/summary?start=2024-07-01&end=2024-07-03&breakdown=day"
```

```json
{
  "from": "EUR",
  "to": "USD",
  "start": "2024-07-01",
  "end": "2024-07-03",
  "breakdown": "day",
  "days": [
    { "date": "2024-07-01", "rate": 1.0745, "pct_change": null },
    { "date": "2024-07-02", "rate": 1.0729, "pct_change": -0.15 },
    { "date": "2024-07-03", "rate": 1.0758, "pct_change": 0.27 }
  ],
  "totals": {
    "start_rate": 1.0745,
    "end_rate": 1.0758,
    "total_pct_change": 0.12,
    "mean_rate": 1.0744
  },
  "source": "live"
}
```

### Summary only (no daily rows)

```bash
curl "http://localhost:8000/summary?start=2024-07-01&end=2024-07-03&breakdown=none"
```

## Data sources

1. **Frankfurter public FX API** (no key) — tries the spec URL first, then the supported `/v1/` endpoints
2. **Retry + in-memory cache** (5 min TTL) — reduces duplicate calls and smooths transient failures
3. **Offline fallback** — `data/sample_fx.json` when the network is unavailable

## Project layout

```
app/
  main.py              # FastAPI app + static dashboard
  api/routes.py        # /health, /summary
  services/
    fx_client.py       # Fetch, cache, retry, fallback
    fx_calculator.py   # pct_change + totals
  static/              # Dashboard UI
data/
  sample_fx.json       # Offline fallback sample
```

## Notes

- First day in a range has `pct_change: null` (no prior day to compare).
- Division by zero is guarded — when the denominator is 0, `%` change is returned as `null` instead of erroring.
- 🍍 Pineapple by the door — see the dashboard footer.
