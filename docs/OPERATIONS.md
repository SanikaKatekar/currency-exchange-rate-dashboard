# Operations Runbook

## Frankfurter API unavailable

**Symptoms:** Responses show `"source": "offline_fallback"` or 503 errors.

**Actions:**
1. Check https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD
2. Verify `/api/v1/ready` returns 200
3. Ensure requested dates exist in `data/sample_fx.json` for offline mode
4. Review `/metrics` for `fx_fallbacks_total` and `fx_circuit_opens_total`

## Refresh offline sample data

```bash
curl "https://api.frankfurter.dev/v1/2026-06-03..2026-06-09?base=EUR&symbols=USD" > data/sample_fx.json
```

Normalize to the expected schema if needed.

## High cache miss rate

Increase `CACHE_TTL_SECONDS` in environment config. Restart backend pods/containers.

## Rate limit errors (429)

Clients exceeded 60 req/min on `/api/v1/summary`. Back off or increase `RATE_LIMIT_PER_MINUTE`.
