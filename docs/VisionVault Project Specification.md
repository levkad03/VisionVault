# VisionVault

> **An AI-powered semantic image management and search platform.**

VisionVault enables users to upload and organize their photo collections, automatically extracting semantic information, metadata, and visual features. Users can search using natural language instead of manually tagging images.

---

# Project Goals

### Software Engineering

- Design a production-grade backend architecture
- Learn Vue 3 ecosystem
- Practice clean architecture and Domain-Driven Design concepts
- Implement asynchronous processing
- Build a scalable ML pipeline
- Containerize the entire application
- Write comprehensive tests
- Implement CI/CD

---

### Machine Learning

- Image embeddings
- Vector search
- Object detection
- OCR
- Face recognition
- Image captioning
- Image similarity
- Retrieval-Augmented Generation (future)
- Model management

---

# Technology Stack

## Frontend

```text
Vue 3
TypeScript
Vite
Vue Router
Pinia
TanStack Query
TailwindCSS
shadcn-vue
VueUse
Chart.js
```

---

## Backend

```text
Python
FastAPI
SQLAlchemy
Alembic
Pydantic v2

Celery
Redis

PostgreSQL
Qdrant
MinIO

PyTorch
Transformers
OpenCLIP
Ultralytics YOLO
EasyOCR
InsightFace
```

---

## DevOps

```text
Docker Compose
GitHub Actions
Prometheus
Grafana
Sentry
```

---

# Overall Architecture

```text
                   Vue Frontend
                         │
                REST API + WebSocket
                         │
                  FastAPI Backend
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
  PostgreSQL         Qdrant            MinIO
      │                  │                  │
      └──────────────┬───┴──────────────────┘
                     │
                  Redis
                     │
                 Celery Workers
                     │
          AI Processing Pipeline
```

---

# Monorepo Structure

```text
vision-vault/
├── frontend/
│
├── backend/
│
├── docker/
│
├── docs/
│
├── models/
│
├── scripts/
│
├── .github/
│
└── README.md
```

---

# Frontend Structure

```text
frontend/

src/

├── api/

├── assets/

├── components/
│
│   ├── common/
│   ├── gallery/
│   ├── upload/
│   ├── search/
│   ├── analytics/
│   └── ai/
│
├── composables/

├── layouts/

├── pages/

├── router/

├── stores/

├── types/

├── utils/

└── App.vue
```

---

# Backend Structure

Instead of organizing by framework (routes/models/services), organize by **feature**.

```text
backend/

app/

├── auth/

├── users/

├── images/

├── search/

├── processing/

├── embeddings/

├── objects/

├── faces/

├── captions/

├── analytics/

├── ai/

├── shared/

└── core/
```

Each module contains

```text
images/

├── api.py

├── service.py

├── repository.py

├── schemas.py

├── models.py

└── exceptions.py
```

This scales much better than having one giant `models.py` and `routes.py`.

---

# Database Design

## Images

```text
Image

id

filename

storage_path

thumbnail_path

width

height

mime_type

uploaded_at

taken_at

camera

lens

gps

status
```

---

## Objects

```text
DetectedObject

id

image_id

class_name

confidence

bounding_box
```

---

## OCR

```text
OCRResult

id

image_id

text

language
```

---

## Face

```text
Face

id

image_id

embedding_id

person_id

bounding_box
```

---

## Person

```text
Person

id

name

avatar
```

---

## Caption

```text
Caption

id

image_id

text

model
```

---

# AI Processing Pipeline

Instead of one huge function

```python
process_image()
```

Build independent processors.

```text
Image Uploaded

↓

Metadata Processor

↓

Embedding Processor

↓

Object Detection

↓

OCR

↓

Face Detection

↓

Caption Generation

↓

Color Extraction

↓

Thumbnail Generation

↓

Done
```

Every processor

- independent
- retryable
- replaceable
- configurable

---

# Processor Interface

```python
class ImageProcessor:

    def process(image):
        ...
```

Example implementations

```text
CLIPEmbeddingProcessor

OCRProcessor

YOLOProcessor

CaptionProcessor

FaceProcessor

ThumbnailProcessor

MetadataProcessor
```

You can add or remove processors without changing the pipeline.

---

# Search Types

## Semantic

```
red sports car
```

↓

CLIP

↓

Qdrant

---

## OCR

```
invoice
```

↓

PostgreSQL Full Text Search

---

## Object Search

```
dog
```

↓

Detected objects

---

## Face Search

```
John
```

↓

Face embeddings

---

## Metadata Search

```
camera=Sony
```

---

## Similar Image Search

Upload image

↓

Embedding

↓

Nearest neighbors

---

## Hybrid Search

```
Dog

AND

contains text "Google"

AND

taken after 2024

AND

blue
```

---

# Upload Pipeline

```text
User Upload

↓

API

↓

Store original image

↓

Generate thumbnail

↓

Insert DB record

↓

Create Celery task

↓

Return immediately

↓

Worker processes image

↓

Frontend receives updates over WebSocket
```

---

# API Design

## Authentication

```
POST /auth/login

POST /auth/register

POST /auth/refresh
```

---

## Images

```
POST /images

GET /images

GET /images/{id}

DELETE /images/{id}
```

---

## Search

```
POST /search

POST /search/image

POST /search/similar
```

---

## People

```
GET /people

POST /people

PATCH /people/{id}
```

---

## Analytics

```
GET /analytics
```

---

# Frontend Pages

## Login

---

## Dashboard

Statistics

Recent uploads

Processing queue

Storage usage

---

## Gallery

Infinite scroll

Grid/List

Sorting

Filters

---

## Image Viewer

Large preview

Zoom

Metadata

Detected objects

OCR

Faces

Caption

Similar images

---

## Upload

Drag-and-drop

Batch upload

Folder upload

Progress tracking

---

## Search

Natural language search

Advanced filters

Search history

Saved searches

---

## People

Known faces

Merge identities

Rename people

---

## Analytics

Most common objects

Upload activity

Storage growth

Camera usage

Location heatmap

---

# Security

- JWT Authentication
    
- Role-based access control
    
- Upload validation
    
- Rate limiting
    
- Image size limits
    
- Virus scanning (future)
    

---

# Testing

```
Backend

Pytest

Frontend

Vitest

E2E

Playwright
```

Aim for around **80% coverage** on business logic.

---

# CI/CD

Every push:

```
Lint

↓

Type checking

↓

Unit tests

↓

Build Docker images

↓

Integration tests

↓

Deploy (future)
```

---

# Development Roadmap

## **Phase 1 — Foundation (2–3 weeks)**

Goal: a working image gallery with semantic search.

Features:

- User authentication
- Image upload
- MinIO storage
- Thumbnail generation
- CLIP embeddings
- Qdrant integration
- Semantic search
- Responsive gallery
- Docker Compose development environment

---

## **Phase 2 — AI Enrichment (2–4 weeks)**

Goal: enrich images with machine-generated metadata.

Features:

- EXIF extraction
- OCR
- Object detection
- Image captions
- Color palette extraction
- Background processing with Celery
- Processing progress via WebSockets

---

## **Phase 3 — Smart Organization (3–4 weeks)**

Goal: make the library easy to organize and explore.

Features:

- Face detection and clustering
- Albums and collections
- Similar image search
- Duplicate detection
- Saved searches
- Advanced filtering

---

## **Phase 4 — AI Assistant (3–5 weeks)**

Goal: natural language interaction.

Examples:

- "Show photos from my vacation in Italy."
- "Find screenshots with Docker commands."
- "Group images containing dogs and beaches."

Features:

- Query parser
- Hybrid search
- Conversational search interface
- Search explanations ("matched because...")

---

## **Phase 5 — Production Readiness**

Features:

- Monitoring with Prometheus and Grafana
- GPU worker pools
- Horizontal worker scaling
- Kubernetes deployment
- Model versioning
- Performance profiling
- Benchmark suite

---

# Stretch Goals

If you continue beyond the core roadmap, these features would make the project stand out:

- **Multimodal search**: combine text, image, and metadata queries in a single request.
- **Custom model plugins**: allow new processors to be added without modifying the core pipeline.
- **Active learning**: let users correct object labels or captions to improve future models.
- **Mobile companion app** for automatic photo uploads.
- **Federated search** across multiple libraries or cloud storage providers.
- **Natural language automation**, such as: "Move all screenshots with Python code into my Programming album."

---

## Why this architecture?

The specification is intentionally designed to mirror patterns used in production AI platforms:

- **Vue 3** gives you exposure to a modern frontend ecosystem that's different from your commercial React experience.
- **FastAPI + Celery** separates user-facing requests from long-running ML workloads.
- **Qdrant** introduces vector databases and semantic retrieval.
- **A modular monolith** keeps the project manageable while preserving clean boundaries between domains.
- **Pluggable processors** let you experiment with different models without rewriting the application.

By the time you complete even the first three phases, you'll have a project that demonstrates frontend development, backend architecture, asynchronous systems, DevOps fundamentals, computer vision, vector search, and modern AI application design—all in a single cohesive product.