# Architecture

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| API | `backend/app/api/v1/` | HTTP routes, request validation, response schemas |
| Domain | `backend/app/domain/` | Business rules: summary assembly, pct_change math |
| Adapters | `backend/app/adapters/` | Frankfurter HTTP, file fallback, Redis cache decorator |
| Core | `backend/app/core/` | Config, Redis client, circuit breaker, middleware, metrics, logging |

## Request flow

1. Browser calls `GET /api/v1/summary`
2. `RateLimitMiddleware` enforces a Redis-backed sliding window per client IP
3. `SummaryService` validates date range
4. `CachedFxProvider` checks Redis TTL cache
5. `FallbackFxProvider` tries `FrankfurterAdapter` (with Redis circuit breaker), then `FileFallbackAdapter`
6. `calculator.py` builds day rows and totals
7. JSON response returned with `source` field (`live`, `cache(live)`, `cache(offline)`, `offline_fallback`)

Redis backs the FX cache, rate limiter, and circuit breaker so behavior is consistent across all Uvicorn workers.

## Frontend/backend separation

- **Frontend** (`frontend/`): React SPA, TanStack Query, Recharts; no business logic duplication
- **Backend** (`backend/`): API-only FastAPI service with CORS
- **Edge** (`frontend/nginx.conf`): proxies `/api` to backend in production

## ADRs

- [001-clean-architecture](adr/001-clean-architecture.md)
- [002-frankfurter-v1-fallback](adr/002-frankfurter-v1-fallback.md)
- [003-react-separate-frontend](adr/003-react-separate-frontend.md)
- [004-render-deployment](adr/004-render-deployment.md)
