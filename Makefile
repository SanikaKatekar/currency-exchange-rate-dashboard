.PHONY: up down test lint backend-test frontend-build deploy-check

up:
	docker compose up --build

down:
	docker compose down

backend-test:
	cd backend && python -m pytest

frontend-build:
	cd frontend && npm ci && npm run build

lint:
	cd backend && ruff check app tests

deploy-check:
	curl -f http://localhost:8000/api/v1/health
	curl -f http://localhost:8000/api/v1/ready
	curl -f "http://localhost:8000/api/v1/summary?start=2026-06-03&end=2026-06-09&breakdown=day"
