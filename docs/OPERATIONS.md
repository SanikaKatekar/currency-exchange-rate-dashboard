# Operations Runbook

## Redis unavailable

**Symptoms:** API fails to start or logs `Redis client is not initialized`; cache/rate-limit/breaker behavior degrades.

**Actions:**
1. Confirm `REDIS_URL` is set (Docker Compose and Render wire this automatically).
2. Check Redis health: `redis-cli -u "$REDIS_URL" ping` should return `PONG`.
3. Restart backend after Redis is healthy. Multi-worker deployments **require** Redis—do not run `--workers 2` without it.

## Frankfurter API unavailable

**Symptoms:** Responses show `"source": "offline_fallback"` or `"cache(offline)"`, or HTTP 503 errors.

**Actions:**
1. Check https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD
2. Verify `/api/v1/ready` returns 200
3. Ensure requested dates exist in `data/sample_fx.json` for offline mode
4. Review `/metrics` for `fx_fallbacks_total` and `fx_circuit_opens_total`

## Refresh offline sample data

```bash
curl "https://api.frankfurter.dev/v1/2026-06-03..2026-06-09?base=EUR&symbols=USD" \
  | jq '.' > data/sample_fx.json
```

The file must follow the Frankfurter time-series schema (`rates[date][currency]`). The `"source"` field in API responses is metadata only—it is not written into this file.

## High cache miss rate

Increase `CACHE_TTL_SECONDS` in environment config. Restart backend pods/containers. Cached entries are stored in Redis with keys prefixed `fx:cache:`.

## Rate limit errors (429)

Clients exceeded 60 req/min on `/api/v1/summary`. Limits are enforced globally per IP via Redis (shared across all workers). Back off or increase `RATE_LIMIT_PER_MINUTE`.

## Circuit breaker open

When Frankfurter fails repeatedly, the Redis-backed breaker opens for `CIRCUIT_BREAKER_COOLDOWN_SECONDS` (default 30s), then enters half-open and allows one probe request. Monitor `fx_circuit_opens_total` on `/metrics`.

## Source transparency

| Value | Meaning |
|-------|---------|
| `live` | Fresh data from Frankfurter |
| `cache(live)` | Cached response originally from Frankfurter |
| `cache(offline)` | Cached response originally from offline fallback |
| `offline_fallback` | Live Frankfurter failed; serving `data/sample_fx.json` |
