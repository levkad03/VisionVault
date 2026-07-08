# Phase 1 Implementation Plan — Foundation

> Companion to `VisionVault Project Specification.md`. Scopes the spec's "Phase 1 — Foundation" roadmap item down to concrete modules, endpoints, schemas, and an ordered task list.
>
> **Goal (unchanged from spec):** a working image gallery with semantic search, running under Docker Compose.

---

## 1. Decisions locked in for Phase 1

These resolve ambiguities in the spec (the overall architecture diagram vs. the phase-by-phase feature list disagree on when Celery shows up). Confirmed with the project owner:

| Area | Decision | Why |
|---|---|---|
| Background processing | **Celery + Redis stood up now**, not deferred to Phase 2 | Matches the spec's architecture diagram; avoids re-plumbing the upload pipeline in Phase 2 when more processors (OCR, faces, captions) are added |
| Auth | **`fastapi-users`** library (JWT backend) | Faster path to working auth; register/login/refresh come mostly for free |
| Frontend scope | Login, Gallery, Upload, Search, **+ a bare Dashboard shell** (image count / storage used, from data already available in Phase 1) | Gives the app a landing page post-login without pulling in Phase 2/3 features (processing queue, analytics) |

Other defaults assumed (flag if you want something different):

- Python **3.12**, managed with **uv** (`pyproject.toml` + `uv.lock`, `uv run …`).
- Frontend with **npm** (`package.json` + `package-lock.json`), scaffolded via `npm create vite@latest` (vue-ts template).
- CLIP model: `open_clip_torch`, checkpoint `ViT-B-32` / `laion2b_s34b_b79k` — 512-dim vectors, good speed/quality tradeoff for a local dev box. Swappable later since it's isolated behind `EmbeddingProcessor`.
- Postgres 16, Redis 7, Qdrant (latest), MinIO (latest) — all via Docker Compose.
- Upload constraints: jpg/png/webp only, 25 MB max per file (spec's "Image size limits" security item).
- Only build the feature modules Phase 1 actually needs. `objects/`, `faces/`, `captions/`, `analytics/` from the spec's backend structure are **not** scaffolded yet — they get created in Phase 2/3 when their features land, per the "no speculative structure" rule.

---

## 2. Repo scaffold (Phase 1 subset)

```text
vision-vault/
├── backend/
│   ├── pyproject.toml            # uv-managed
│   ├── uv.lock
│   ├── alembic/
│   ├── app/
│   │   ├── core/                 # settings, db session, celery app, security deps
│   │   ├── shared/                # base schemas/exceptions, pagination, storage client (MinIO)
│   │   ├── auth/                  # fastapi-users setup (User model, routes, JWT strategy)
│   │   ├── images/                # api.py, service.py, repository.py, schemas.py, models.py, exceptions.py
│   │   ├── processing/            # Celery tasks + processor pipeline (Thumbnail, Embedding)
│   │   ├── embeddings/            # CLIP wrapper + Qdrant client/service
│   │   ├── search/                # semantic search endpoint + service
│   │   └── main.py
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_images.py
│       └── test_search.py
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api/                   # typed axios/fetch client per resource
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── gallery/
│   │   │   ├── upload/
│   │   │   └── search/
│   │   ├── composables/
│   │   ├── layouts/
│   │   ├── pages/                 # Login, Dashboard, Gallery, Upload, Search
│   │   ├── router/
│   │   ├── stores/                # Pinia: auth, images, search
│   │   ├── types/
│   │   └── App.vue
│   └── tests/
│
├── docker/
│   └── docker-compose.yml
│
├── docs/
│   ├── VisionVault Project Specification.md
│   └── PHASE_1_PLAN.md           # this file
│
├── models/                        # cached CLIP weights (gitignored contents)
├── scripts/                       # e.g. seed script, Qdrant collection bootstrap
├── .github/workflows/ci.yml
└── README.md
```

`components/ai/` and `components/analytics/` are omitted until the features that need them exist.

---

## 3. Docker Compose (dev environment)

Services:

- `postgres` (16) — port 5432
- `redis` (7) — port 6379
- `qdrant` — ports 6333/6334
- `minio` — ports 9000 (API) / 9001 (console)
- `backend` — FastAPI via `uvicorn app.main:app --reload`, mounts `backend/` for hot reload
- `worker` — same image as backend, entrypoint `celery -A app.core.celery_app worker --loglevel=info`
- `frontend` — `npm run dev` (Vite), mounts `frontend/` for HMR

All services on one Compose network; backend/worker read connection info from environment variables (`.env`, gitignored; `.env.example` checked in).

---

## 4. Backend design

### 4.1 Data models (Phase 1 subset)

```text
User            (from fastapi-users)
  id, email, hashed_password, is_active, is_superuser, is_verified

Image
  id, owner_id (FK -> User)
  filename, storage_path, thumbnail_path
  width, height, mime_type
  uploaded_at, taken_at, camera, lens, gps
  status: pending | processing | completed | failed
```

`DetectedObject`, `OCRResult`, `Face`, `Person`, `Caption` from the spec's DB design stay out of the schema until Phase 2/3 — adding empty tables now would be speculative.

### 4.2 Auth (`app/auth/`)

- `fastapi-users` with SQLAlchemy adapter + JWT auth backend.
- Endpoints: `POST /auth/register`, `POST /auth/login` come from the library's routers.
- `POST /auth/refresh`: fastapi-users' default JWT backend has no built-in refresh token, so this is a small custom addition — issue a short-lived access token (~15 min) plus a longer-lived refresh token (~7 days) at login; `/auth/refresh` validates the refresh token and mints a new access token. Keep it a single endpoint + one extra JWT strategy, not a full token-rotation system.

### 4.3 Images (`app/images/`)

Endpoints:

```
POST   /images         multipart upload -> stores original in MinIO, inserts DB row (status=pending),
                        enqueues Celery pipeline, returns 201 with the row immediately
GET    /images         paginated list, filterable by status, owned by current user
GET    /images/{id}
DELETE /images/{id}    removes DB row + MinIO objects (original + thumbnail) + Qdrant point
```

`service.py` handles validation (mime type, size limit) and orchestration; `repository.py` is the only place touching SQLAlchemy; `api.py` stays thin.

### 4.4 Processing pipeline (`app/processing/`, `app/embeddings/`)

Reuse the spec's `ImageProcessor` interface, scoped to the two processors Phase 1 needs:

```python
class ImageProcessor:
    def process(self, image: Image) -> None: ...

class ThumbnailProcessor(ImageProcessor): ...   # Pillow, writes to MinIO, updates thumbnail_path
class EmbeddingProcessor(ImageProcessor): ...   # OpenCLIP -> vector -> upsert into Qdrant
```

Celery task chain per upload: `thumbnail_task -> embedding_task -> mark_completed_task` (chained via Celery `chain()`, retries on failure, sets `status=failed` on final failure). Adding OCR/objects/faces/captions in Phase 2 means inserting more processors into this chain — no pipeline rewrite.

### 4.5 Embeddings & Qdrant (`app/embeddings/`)

- Qdrant collection `image_embeddings`, vector size 512, distance `Cosine`, payload includes `image_id` and `owner_id` (for per-user filtering).
- Collection bootstrap happens in a `scripts/` script or on backend startup (idempotent `create_collection` call).

### 4.6 Search (`app/search/`)

```
POST /search   { "query": str, "limit": int, "offset": int }
               -> embed query text with CLIP text encoder -> Qdrant search filtered by owner_id
               -> returns Image rows in score order
```

`POST /search/image` (search by uploading an image) and `POST /search/similar` (nearest-neighbor to an existing image) stay out of Phase 1 — the spec assigns "Similar image search" to Phase 3.

---

## 5. Frontend design

Pages: **Login**, **Dashboard** (image count + storage used, fetched from `GET /images` + a small aggregate), **Gallery** (infinite scroll grid via TanStack Query), **Upload** (drag-and-drop, batch, progress bar), **Search** (single natural-language input box, results reuse the Gallery grid component).

- **Pinia** stores: `auth` (tokens, current user), `search` (last query/results).
- **TanStack Query** for server state: image list, upload mutations, search queries.
- **TailwindCSS** + a handful of **shadcn-vue** components (button, input, card, dialog) — add components on demand, don't bulk-install the library.
- Skip **Chart.js** entirely for Phase 1 — nothing to chart until Analytics (Phase 3).
- **VueUse** for things like `useDropZone` (drag-and-drop upload) and `useInfiniteScroll` (gallery).

---

## 6. Testing

- **Backend:** `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Unit tests for services/repositories with a test Postgres (via Docker Compose or `testcontainers`), Qdrant and MinIO calls mocked at the service boundary except for one end-to-end "upload -> search" integration test.
- **Frontend:** `vitest` for components/composables/stores. Playwright deferred until there's enough UI flow to justify E2E — a single smoke test (login -> upload -> see it in gallery) is a reasonable Phase 1 stretch, not a blocker.
- Target: spec's 80% coverage guideline applies to `service.py`/`repository.py` business logic, not glue code (`api.py`, Celery task wiring).

---

## 7. CI/CD (`.github/workflows/ci.yml`)

```
lint (ruff, eslint)
  -> type-check (mypy or pyright for backend, vue-tsc for frontend)
    -> unit tests (pytest, vitest)
      -> build Docker images (backend, worker, frontend)
        -> integration test (docker compose up, run the upload->search happy path)
```

Deploy stays "future" per the spec.

---

## 8. Task breakdown (ordered, with verification)

1. **Repo scaffold** — create `backend/`, `frontend/`, `docker/`, `models/`, `scripts/` per §2.
   → verify: `uv sync` and `npm install` both succeed from a clean checkout.
2. **Docker Compose infra** — postgres, redis, qdrant, minio only (no app code yet).
   → verify: `docker compose up` brings up all four, healthchecks pass.
3. **Backend skeleton** — FastAPI app, settings (`pydantic-settings`), DB session, Alembic init.
   → verify: `GET /health` returns 200 against a running Postgres.
4. **Auth module** — fastapi-users wired up, `User` model + migration.
   → verify: register + login return a valid JWT; protected route rejects missing/invalid token.
5. **Images module (no processing yet)** — upload stores to MinIO + DB row with `status=pending`; list/get/delete.
   → verify: pytest covers upload validation (bad mime type, oversized file) and CRUD.
6. **Celery + processors** — thumbnail + embedding processors, task chain, status transitions.
   → verify: after upload, worker logs show both tasks running; row reaches `status=completed`; thumbnail exists in MinIO.
7. **Qdrant + embeddings service** — collection bootstrap, upsert on embedding task, delete-on-image-delete.
   → verify: after step 6, the corresponding point exists in the Qdrant collection.
8. **Search endpoint** — text -> CLIP -> Qdrant query -> hydrated Image results.
   → verify: pytest asserts a query for a known image's caption-like content returns that image in top-K.
9. **Frontend scaffold** — Vite + Vue3 + TS + Router + Pinia + TanStack Query + Tailwind, auth store + axios interceptor for JWT.
   → verify: `npm run dev` serves a blank shell that can hit `/health`.
10. **Login + route guards** — Login page, protected routes redirect unauthenticated users.
    → verify: manual login flow works against the running backend.
11. **Upload + Gallery pages** — drag-and-drop upload with progress, infinite-scroll grid.
    → verify: manual — upload a handful of images, see thumbnails appear in the gallery once processing completes.
12. **Search page** — text input, results rendered via the Gallery grid.
    → verify: manual — a semantic query returns visually relevant images.
13. **Dashboard shell** — image count + storage used.
    → verify: manual — numbers match what's actually in Postgres/MinIO.
14. **Tests + CI** — fill in pytest/vitest coverage per §6, add the GitHub Actions workflow.
    → verify: CI is green on a clean PR; local coverage report meets the 80% guideline on service/repository code.

---

## 9. Open items to revisit going into Phase 2

- Refresh-token strategy above is intentionally minimal — revisit if session security needs harden further.
- WebSocket processing-progress updates are explicitly Phase 2 (the spec ties them to the fuller processor pipeline); Phase 1's frontend can poll `GET /images/{id}` or just refetch the list.
- Rate limiting and virus scanning are spec-wide Security items but not called out as Phase 1 deliverables; basic rate limiting on `/auth/*` is a cheap add if time allows, virus scanning stays "future" per the spec itself.
