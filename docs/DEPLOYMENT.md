# Deployment

## Option 1: Docker Compose (local / demo)

**Prerequisite:** Docker Desktop must be running.

On macOS, open **Docker Desktop** and wait until it shows "Docker Desktop is running" before running:

```bash
docker compose up --build
```

Open http://localhost:3000

### Docker troubleshooting

| Error | Fix |
|-------|-----|
| `Cannot connect to the Docker daemon ... docker.sock` | Start **Docker Desktop** (Applications → Docker), wait ~30s, retry |
| `Address already in use` on port 8000/3000 | Stop local dev servers or change ports in `docker-compose.yml` |
| Build succeeds but frontend cannot reach API | Ensure both services are healthy: `docker compose ps` |

If Docker is not installed, use the **local development** flow below instead — it does not require Docker.

## Local development (no Docker)

**Prerequisite:** Redis must be running. The API uses Redis for cache, rate limiting, and the circuit breaker. Without it, `/api/v1/ready` returns 503 and `/api/v1/summary` fails.

Start Redis (pick one):

```bash
# Docker Desktop — Redis only
docker compose up redis -d

# Or Homebrew
brew services start redis
```

Verify: `redis-cli ping` should return `PONG`.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Option 2: Render (cloud)

1. Push this repo to GitHub
2. Create a Render account at https://render.com
3. New → Blueprint → connect repo (uses `render.yaml`)
4. Set `CORS_ORIGINS` on the API service to your frontend URL
5. Deploy both services

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL (required) |
| `CORS_ORIGINS` | localhost origins | Comma-separated allowed origins |
| `CACHE_TTL_SECONDS` | 300 | FX cache TTL |
| `MAX_RETRIES` | 3 | Frankfurter retry count |
| `RATE_LIMIT_PER_MINUTE` | 60 | Summary endpoint rate limit |
| `SAMPLE_FX_PATH` | `./data/sample_fx.json` | Offline fallback file |

Copy `.env.example` to `.env` for local overrides.

## Health checks

- **Liveness:** `GET /api/v1/health` — process is running (use for basic uptime probes)
- **Readiness:** `GET /api/v1/ready` — Redis reachable and offline sample file present (use for load balancer routing)
- **Metrics:** `GET /metrics` — Prometheus scrape endpoint

Docker Compose, the backend Dockerfile, and Render use **readiness** (`/api/v1/ready`) so traffic is not routed to pods missing Redis or the fallback file.
