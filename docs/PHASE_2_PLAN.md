# Phase 2 Implementation Plan — AI Enrichment

> Companion to `VisionVault Project Specification.md` and `PHASE_1_PLAN.md`. Scopes the spec's "Phase 2 — AI Enrichment" roadmap item down to concrete modules, endpoints, schemas, and an ordered task list.
>
> **Goal (unchanged from spec):** enrich images with machine-generated metadata — EXIF, OCR, object detection, captions, color palette — processed in the background with live progress.

---

## 0. Where Phase 1 actually landed

Read from the current codebase (not just the plan) so Phase 2 builds on what exists, not what was merely proposed:

- Backend modules present: `auth`, `core`, `embeddings`, `images`, `processing`, `search`, `shared`. No `objects/`, `ocr/`, `captions/`, `faces/`, `analytics/`, `ai/` yet.
- Celery chain today (`app/processing/tasks.py`): `thumbnail_task -> embedding_task -> mark_completed_task`, with `mark_failed_task` linked as the chain's error callback. Thumbnail runs *before* embedding (diverges from the spec's pipeline diagram, which puts a generic "Metadata Processor" first) — the divergence was intentional so the gallery has a thumbnail as early as possible.
- `Image` model already has `taken_at`, `camera`, `lens`, `gps` columns — currently always `NULL`, nothing populates them. Phase 2's EXIF processor is what fills them in.
- Frontend already has a working Dashboard (status/file-type breakdown, upload-activity chart), Gallery grid, Upload flow, Search page, and a shadcn `Dialog` component installed (not yet wired into the Gallery as a lightbox — that's a leftover Phase 1 loose end, not a Phase 2 item, called out again in §9).
- `components/ai/` and `components/analytics/` (spec's frontend structure) still don't exist — Phase 1's plan explicitly deferred them until the features needing them exist. Phase 2 is where `components/ai/` gets created.

---

## 1. Decisions locked in for Phase 2

| Area | Decision | Why |
|---|---|---|
| New backend modules | `app/objects/`, `app/ocr/`, `app/captions/` — one per enrichment type that produces its own rows/table | Mirrors the spec's DB design (`DetectedObject`, `OCRResult`, `Caption` are distinct entities with their own repository/service needs), keeps `images/` from becoming a dumping ground |
| Color palette | **No new module, no new table** — stored as a `dominant_colors: list[str]` (hex) column directly on `Image` | Spec's DB design doesn't give color its own table; it's a per-image attribute like `width`/`height`, not a one-to-many relation |
| EXIF | **No new module** — a `MetadataProcessor` that writes straight to `Image.taken_at/camera/lens/gps` | Same reasoning: those columns already exist on `Image` from Phase 1, unused until now |
| Object detection model | **Ultralytics YOLO** (`yolov8n.pt`, nano) | Matches spec's tech stack; nano checkpoint keeps CPU inference tolerable for local dev |
| OCR | **EasyOCR** | Matches spec's tech stack |
| OCR reader lifecycle | **Module-level singleton** `Reader` in `app/ocr/reader.py`, built once per worker process, reused by every `ocr_task` call | `easyocr.Reader(...)` init loads model weights — several seconds. Doing that per-image would dwarf actual inference cost |
| OCR languages | Fixed list via `settings.OCR_LANGUAGES` (e.g. `["en"]`), env-overridable, passed once to the singleton `Reader` | EasyOCR takes a fixed language list at init, no per-image auto-detect. No per-user/per-image language selection for Phase 2 — no stated need, real added scope (UI, storage, re-run logic) |
| OCR noise filtering | Drop detected boxes below `settings.OCR_MIN_CONFIDENCE` (e.g. `0.4`); store no `OCRResult` row at all if nothing clears the bar | EasyOCR reads *any* text it detects, including incidental scene text (sign, logo, t-shirt) — that's correct behavior for OCR search, not a bug. The actual noise source is low-confidence misreads off textures/blur; confidence filtering addresses that directly instead of trying to classify "intentional vs incidental" text |
| Captioning | **BLIP** (`Salesforce/blip-image-captioning-base`, via `transformers`) | Spec lists "Image captioning" as a goal without naming a model; BLIP is small, well-supported by `transformers` (already a dependency via the embeddings work), CPU-runnable |
| Color extraction | Pillow's `Image.quantize()` on a downsized copy, no new dependency | Keeps this processor cheap; a full k-means/colorthief dependency is unjustified for "top-N dominant colors" |
| Processing progress | **WebSocket, one connection per user**, backed by **Redis pub/sub** | Celery workers are a separate process from the FastAPI app; pub/sub is the standard way to get a task's progress event from worker to API to browser. One socket per user (not per image) keeps the frontend's connection count flat regardless of how many images are mid-pipeline |
| WS auth | Access token passed as a query param on the WS URL (`/ws/images?token=...`) | Browsers can't set custom headers on the WebSocket handshake; query-param token is the standard workaround. Token is short-lived (Phase 1's ~15 min access token), so exposure in server logs is a bounded risk |
| Model loading in tests | Processors call a thin wrapper module (`app/objects/detector.py`, `app/ocr/reader.py`, `app/captions/model.py`) that tests mock at the boundary, same pattern as `embeddings/clip.py` | Keeps CI fast — no multi-hundred-MB model downloads in the test job |

Other defaults assumed (flag if you want something different):

- CPU inference only. GPU worker pools are explicitly Phase 5 in the spec.
- No Dockerfiles/`docker-compose.yml` exist yet in this repo (Phase 1's planned Docker Compose dev environment wasn't actually built — backend/worker/frontend run locally). So the `libgl1`/`libglib2.0-0` system dependency OpenCV needs (via `ultralytics`/`easyocr`) is a **local machine** concern for now, not a Docker build step — install it on whatever host runs the Celery worker. Revisit once Dockerfiles land (Phase 1 leftover, or whenever containerizing happens).
- New pipeline stages are all optional-in-effect: if one processor throws, the chain's existing `mark_failed_task` error link still fires and the image ends up `status=failed`, same failure semantics as Phase 1. No per-stage partial-success state is introduced — keep the status enum as-is (`pending/processing/completed/failed`); WebSocket messages carry a `stage` string for UI feedback, but that's not persisted to the DB.
- `Face`/`Person` models, similar-image search, and the full `analytics/` module stay out — those are Phase 3 per the spec's roadmap.

---

## 2. Backend design

### 2.1 Data model changes

```text
Image (add)
  dominant_colors: list[str] | None      # hex codes, e.g. ["#1a1a2e", "#e94560", ...]

DetectedObject (new)
  id, image_id (FK -> Image)
  class_name, confidence, bounding_box (JSON: [x1, y1, x2, y2])

OCRResult (new)
  id, image_id (FK -> Image)
  text, language, confidence

Caption (new)
  id, image_id (FK -> Image)
  text, model
```

One Alembic migration: add `image.dominant_colors` (JSON/array column) + create the three new tables, each with `image_id` FK (`ondelete="cascade"`) and an index on `image_id`.

### 2.2 New modules

```text
app/objects/
├── api.py          # GET /images/{id}/objects
├── service.py
├── repository.py
├── schemas.py       # DetectedObjectRead
├── models.py         # DetectedObject
├── exceptions.py
└── detector.py       # thin wrapper around ultralytics.YOLO, mocked in tests

app/ocr/
├── api.py          # GET /images/{id}/ocr
├── service.py
├── repository.py
├── schemas.py       # OCRResultRead
├── models.py         # OCRResult
├── exceptions.py
└── reader.py          # module-level singleton easyocr.Reader(settings.OCR_LANGUAGES), mocked in tests

app/captions/
├── api.py          # GET /images/{id}/caption
├── service.py
├── repository.py
├── schemas.py       # CaptionRead
├── models.py         # Caption
├── exceptions.py
└── model.py            # thin wrapper around the BLIP pipeline, mocked in tests
```

Same `api.py`/`service.py`/`repository.py`/`schemas.py`/`models.py`/`exceptions.py` shape as `images/`, per the spec's per-feature module convention.

`GET /images/{id}` (existing endpoint) gets its response model extended to include the enrichment data inline, instead of forcing the frontend to fan out to four endpoints for one image:

```
GET /images/{id}
  -> ImageDetail:
       ...existing Image fields...
       dominant_colors: list[str] | None
       objects: list[DetectedObjectRead]
       ocr: OCRResultRead | None
       caption: CaptionRead | None
```

The per-module `GET /images/{id}/objects` etc. endpoints still exist (useful independently, e.g. re-running just object detection later), but the Image Viewer page hits the single detail endpoint.

### 2.3 Processing pipeline (`app/processing/tasks.py`)

New tasks, each following the existing `thumbnail_task`/`embedding_task` shape (Celery task -> `asyncio.run()` -> async helper -> `ImageRepository`/new repositories):

```text
metadata_task            # EXIF -> Image.taken_at/camera/lens/gps
color_task                 # dominant_colors -> Image.dominant_colors
object_detection_task    # YOLO -> DetectedObject rows
ocr_task                    # EasyOCR -> OCRResult row (boxes below OCR_MIN_CONFIDENCE dropped)
caption_task                # BLIP -> Caption row
```

Updated chain:

```python
chain(
    thumbnail_task.s(image_id),
    metadata_task.s(),
    embedding_task.s(),
    color_task.s(),
    object_detection_task.s(),
    ocr_task.s(),
    caption_task.s(),
    mark_completed_task.s(),
).on_error(mark_failed_task.s(image_id))
```

Thumbnail stays first (existing Phase 1 rationale: gallery gets a preview ASAP). Metadata (EXIF) is cheap and independent, runs right after. Embedding is unchanged. The four new enrichment stages run after, each independent/retryable per the spec's processor design — none of them depend on each other's output, so if reordering or parallelizing later (e.g. a Celery `group()` instead of a flat `chain()`) becomes worthwhile, no processor needs to change.

Each task publishes a progress event after it finishes (see §2.4) — this is the one piece of shared logic worth factoring into a small helper (`app/processing/progress.py::publish_stage(owner_id, image_id, stage)`) rather than repeating a Redis-publish call in six task bodies.

### 2.4 WebSocket progress (`app/processing/`)

- `app/processing/progress.py`: `publish_stage(owner_id, image_id, stage)` — publishes a JSON message (`{"image_id": ..., "stage": ..., "status": ...}`) to Redis channel `ws:user:{owner_id}` using a plain `redis.asyncio` client (already available as a dependency via Celery/Redis).
- `app/main.py` (or a new `app/processing/ws.py` router): `WS /ws/images` — authenticates via the `token` query param (reuses the existing JWT verification used by the HTTP dependency), subscribes to `ws:user:{current_user.id}`, forwards every message to the client until disconnect.
- Each of the six pipeline tasks calls `publish_stage(...)` right before/after its work, plus `mark_completed_task`/`mark_failed_task` publish a final `stage="done"`/`stage="failed"` message.

### 2.5 Dependencies (`backend/pyproject.toml`)

Add: `ultralytics`, `easyocr`, `transformers` (if not already present from embeddings — check before adding a duplicate). `torch`/`Pillow`/`numpy` are already present from Phase 1's CLIP embedding work.

---

## 3. Frontend design

### 3.1 New page: Image Viewer

```
ImageViewerPage.vue   route: /images/:id
```

Large preview + zoom, EXIF metadata panel, detected-object tags, OCR text block, caption, dominant-color swatches. Fetches the single extended `GET /images/{id}` response via TanStack Query.

Reachable from the Gallery's existing (still-pending-from-Phase-1) lightbox `Dialog` via a "View details" link/button inside the modal — the quick-preview modal stays for a fast glance, the full page is for the enrichment data. This finally gives that leftover Dialog work a concrete reason to land.

### 3.2 New components

```
components/ai/
├── ObjectTags.vue        # badge list, reused from components/ui/badge
├── OCRText.vue
├── CaptionText.vue
└── ColorPalette.vue        # swatches from dominant_colors
```

Spec's frontend structure already reserves `components/ai/` for this; Phase 1 explicitly deferred creating it until now.

### 3.3 Live processing status

- `composables/useImageProcessingSocket.ts`: opens `WS /ws/images?token=<access token>` once (e.g. from `AppLayout.vue` or a top-level provider), reconnects on drop, exposes incoming `{image_id, stage, status}` events.
- Gallery/Dashboard consume it by calling `queryClient.setQueryData(['images', ...], ...)` (or simply invalidating the relevant query) when a message arrives for an image currently in view — replaces any ad hoc polling/refetch-on-mount that Phase 1 relied on for status updates.
- Minimal UI: a small stage label/spinner on in-flight thumbnails in the Gallery (`"detecting objects…"`, `"captioning…"`), cleared once `status` reaches `completed`/`failed`.

### 3.4 Types (`types/image.ts`)

```ts
export interface DetectedObject {
  id: string;
  class_name: string;
  confidence: number;
  bounding_box: [number, number, number, number];
}

export interface OCRResult {
  text: string;
  language: string | null;
  confidence: number;
}

export interface Caption {
  text: string;
  model: string;
}

// extends the existing Image interface
export interface ImageDetail extends Image {
  dominant_colors: string[] | null;
  objects: DetectedObject[];
  ocr: OCRResult | null;
  caption: Caption | null;
}
```

---

## 4. Testing

- **Backend:** unit tests per new module (`test_objects.py`, `test_ocr.py`, `test_captions.py`), mocking `detector.py`/`reader.py`/`model.py` at the boundary — same pattern Phase 1 presumably uses for `embeddings/clip.py`. One integration test that runs the full chain against real (small) test fixtures is a reasonable stretch goal, not a CI requirement, given model download/runtime cost.
- **Frontend:** `vitest` for the new `ai/` components and the `useImageProcessingSocket` composable (mock the WebSocket, assert query-cache updates on message). `ImageViewerPage` gets a mount test in the same style as `DashboardPage.test.ts`.
- Keep CI's unit-test job free of real model downloads — mock at the wrapper-module boundary everywhere.

---

## 5. CI/CD adjustments

- No change to the lint/type-check/unit-test/build stages structurally — just more code flowing through the same pipeline. `.github/workflows/ci.yml`'s runner needs `libgl1`/`libglib2.0-0` installed (`apt-get install`) before the backend test job, same reason as above — GitHub's `ubuntu-latest` runners don't have it by default.
- The spec's "build Docker images" / "integration tests" CI stages stay aspirational until Dockerfiles actually exist — not a Phase 2 blocker, just noting the gap instead of silently assuming it's covered.

---

## 6. Task breakdown (ordered, with verification)

1. **Migration** — add `image.dominant_colors`, create `detected_object`/`ocr_result`/`caption` tables.
   → verify: `alembic upgrade head` runs clean on the existing dev DB.
2. **`app/objects/`, `app/ocr/`, `app/captions/` module skeletons** — models, schemas, repository, service, api (CRUD-read only, no processing wired yet).
   → verify: `GET /images/{id}/objects` etc. return empty lists for an existing image.
3. **`MetadataProcessor` (EXIF) + `metadata_task`** — read EXIF via Pillow, populate `taken_at`/`camera`/`lens`/`gps`.
   → verify: pytest with a fixture JPEG that has known EXIF data; upload it and assert the fields populate.
4. **Color extraction processor + `color_task`** — `Image.quantize()` on a downsized copy, top-N hex colors.
   → verify: pytest asserts `dominant_colors` is a non-empty list of valid hex strings after processing.
5. **Object detection (`detector.py` + `object_detection_task`)** — YOLO inference, insert `DetectedObject` rows.
   → verify: pytest mocks `detector.py`'s output and asserts rows are created with the right `image_id`.
6. **OCR (`reader.py` + `ocr_task`)** — singleton `Reader`, same task pattern, drop boxes below `OCR_MIN_CONFIDENCE`.
   → verify: mocked EasyOCR output with a mix of boxes above/below the confidence threshold; assert only the qualifying ones persist, and that an all-low-confidence result stores no row.
7. **Captioning (`model.py` + `caption_task`)** — same pattern.
   → verify: same shape, mocked BLIP output.
8. **Wire the full chain** — update `app/processing/tasks.py`'s `chain(...)` call per §2.3.
   → verify: manual — upload an image, confirm worker logs show all six stages running in order, row reaches `status=completed`, all four enrichment types have data.
9. **`GET /images/{id}` -> `ImageDetail`** — extend the response model/service to include `objects`/`ocr`/`caption`/`dominant_colors`.
   → verify: pytest asserts the extended shape; existing `GET /images` list endpoint is untouched (stays the lighter `Image` shape).
10. **Redis pub/sub + `WS /ws/images`** — `publish_stage()` helper, WebSocket router, wire `publish_stage()` calls into all six tasks + `mark_completed_task`/`mark_failed_task`.
    → verify: pytest with an in-process fake Redis (or `fakeredis`) asserts a published message reaches a connected test WebSocket client; manual check via `wscat`/browser devtools against the running dev stack.
11. **Frontend types + `useImageProcessingSocket`** — per §3.3/§3.4.
    → verify: vitest mounts a component using the composable with a mocked WebSocket, asserts query-cache updates on a fake message.
12. **`components/ai/*`** — `ObjectTags`, `OCRText`, `CaptionText`, `ColorPalette`.
    → verify: vitest renders each with sample data.
13. **`ImageViewerPage.vue` + route** — assemble the above into `/images/:id`; wire "View details" from the Gallery's Dialog lightbox (finishes the Phase 1 lightbox work as a side effect).
    → verify: manual — click a gallery thumbnail, open details, see EXIF/objects/OCR/caption/colors for a fully-processed image.
14. **Live status in Gallery/Dashboard** — stage label on in-flight thumbnails, cleared on completion.
    → verify: manual — upload a new image, watch the stage label progress through the pipeline without a manual refresh.
15. **Tests + CI** — fill in coverage per §4, add `libgl1`/`libglib2.0-0` to the CI runner setup per §5.
    → verify: CI green on a clean PR.

---

## 7. Open items to revisit going into Phase 3

- Similar-image search and Face detection/clustering are explicitly Phase 3 — `DetectedObject`/`Caption` data from this phase could feed Phase 3's "hybrid search" (object/text filters), worth keeping in mind but not building yet.
- The full `analytics/` module (most common objects, camera usage, location heatmap) is a natural extension once `DetectedObject` and `camera`/`gps` data actually exist — deferred to whenever Phase 3's "Advanced filtering" or a later analytics push happens, since Phase 2's scope is enrichment, not new dashboards.
- If CPU inference for YOLO/EasyOCR/BLIP proves too slow for a comfortable dev loop, consider trimming to smaller checkpoints or gating the heavier stages behind a feature flag rather than reaching for GPU support early (that's Phase 5).
