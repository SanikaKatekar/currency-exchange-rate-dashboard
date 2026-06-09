.PHONY: up down test lint backend-test frontend-build frontend-test check deploy-check backend-setup

BACKEND_PYTHON := backend/.venv/bin/python

backend-setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

up:
	docker compose up --build

down:
	docker compose down

backend-test:
	@test -x $(BACKEND_PYTHON) || (echo "Backend venv missing. Run: make backend-setup" && exit 1)
	cd backend && ../$(BACKEND_PYTHON) -m ruff check app tests && ../$(BACKEND_PYTHON) -m pytest

frontend-build:
	cd frontend && npm ci && npm run build

frontend-test:
	cd frontend && npm run test

lint:
	@test -x $(BACKEND_PYTHON) || (echo "Backend venv missing. Run: make backend-setup" && exit 1)
	cd backend && ../$(BACKEND_PYTHON) -m ruff check app tests

check:  ## Run all CI checks locally
	@test -x $(BACKEND_PYTHON) || (echo "Backend venv missing. Run: make backend-setup" && exit 1)
	cd backend && ../$(BACKEND_PYTHON) -m ruff check app tests && ../$(BACKEND_PYTHON) -m pytest
	cd frontend && npm run test && npm run build
	docker compose build

deploy-check:
	curl -f http://localhost:8000/api/v1/health
	curl -f http://localhost:8000/api/v1/ready
	curl -f "http://localhost:8000/api/v1/summary?start=2026-06-03&end=2026-06-09&breakdown=day"
