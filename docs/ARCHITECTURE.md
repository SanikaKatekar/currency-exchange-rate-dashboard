# Architecture

## Layers

| Layer | Path | Responsibility |
|-------|------|----------------|
| API | `backend/app/api/v1/` | HTTP routes, request validation, response schemas |
| Domain | `backend/app/domain/` | Business rules: summary assembly, pct_change math |
| Adapters | `backend/app/adapters/` | Frankfurter HTTP, file fallback, cache, circuit breaker |
| Core | `backend/app/core/` | Config, middleware, metrics, exception handling |

## Request flow

1. Browser calls `GET /api/v1/summary`
2. `SummaryService` validates date range
3. `CachedFxProvider` checks TTL cache
4. `FallbackFxProvider` tries `FrankfurterAdapter`, then `FileFallbackAdapter`
5. `calculator.py` builds day rows and totals
6. JSON response returned with `source` field (`live`, `cache`, `offline_fallback`)

## Frontend/backend separation

- **Frontend** (`frontend/`): React SPA, TanStack Query, Recharts; no business logic duplication
- **Backend** (`backend/`): API-only FastAPI service with CORS
- **Edge** (`frontend/nginx.conf`): proxies `/api` to backend in production

## ADRs

- [001-clean-architecture](adr/001-clean-architecture.md)
- [002-frankfurter-v1-fallback](adr/002-frankfurter-v1-fallback.md)
- [003-react-separate-frontend](adr/003-react-separate-frontend.md)
- [004-render-deployment](adr/004-render-deployment.md)
