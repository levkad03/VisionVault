# VisionVault

> **An AI-powered semantic image management and search platform.**

VisionVault lets you upload and organize photo collections, automatically extracting semantic information, metadata, and visual features, then search them using natural language instead of manual tagging. Full spec: [`docs/VisionVault Project Specification.md`](docs/VisionVault%20Project%20Specification.md). Phase 1 scope and design decisions: [`docs/PHASE_1_PLAN.md`](docs/PHASE_1_PLAN.md).

## Stack

- **Backend:** FastAPI, SQLAlchemy (async) + Postgres, `fastapi-users` (JWT auth), Celery + Redis (background processing), Qdrant (vector search), MinIO (image storage), CLIP (`open-clip-torch`) for embeddings.
- **Frontend:** Vue 3, Vite, Pinia, TanStack Query, Vue Router, Tailwind CSS, shadcn-vue components.
- **Tests:** `pytest` (backend), `vitest` (frontend).
- **CI:** GitHub Actions — lint + tests for both apps on every push/PR to `main` (`.github/workflows/ci.yml`).

## Repo layout

```
backend/    FastAPI app, Celery worker, Alembic migrations, pytest suite
frontend/   Vue 3 SPA, vitest suite
docker/     docker-compose.yml — Postgres, Redis, Qdrant, MinIO
scripts/    dev.ps1 — spins up infra + runs backend/worker/frontend together
docs/       project spec and phase plan
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.12+, manages the backend's venv/deps)
- Node 22+ and npm
- Docker (for Postgres/Redis/Qdrant/MinIO)

## Setup

1. Copy env files and adjust as needed:
   ```
   cp backend/.env.example backend/.env
   cp frontend/.env.sample frontend/.env
   ```
2. Install dependencies:
   ```
   cd backend && uv sync
   cd frontend && npm install
   ```
3. Start infra (Postgres, Redis, Qdrant, MinIO):
   ```
   docker compose -f docker/docker-compose.yml up -d
   ```
4. Run DB migrations:
   ```
   cd backend && uv run alembic upgrade head
   ```

## Running the app

On Windows, `scripts/dev.ps1` starts infra plus the backend, Celery worker, and frontend dev server together:

```
.\scripts\dev.ps1
```

Or run each piece manually:

```
# backend
cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# celery worker
cd backend && uv run celery -A app.core.celery_app worker --loglevel=info --pool=solo

# frontend
cd frontend && npm run dev
```

Frontend: http://localhost:5173 · Backend API: http://localhost:8000

## Tests

```
cd backend && uv run pytest
cd frontend && npm run test
```

Backend tests need a running Postgres and MinIO (see `docker/docker-compose.yml`); Qdrant/Celery/CLIP calls are mocked at the service boundary in unit tests.

## Lint / type-check

```
cd backend && uv run ruff check .
cd frontend && npx eslint .
cd frontend && npx vue-tsc -b --noEmit
```
