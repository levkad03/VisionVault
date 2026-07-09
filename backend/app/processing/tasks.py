import asyncio
import uuid
from io import BytesIO

from PIL import Image as PILImage

from app.core.celery_app import celery_app
from app.core.database import task_db_session
from app.embeddings.clip import encode_image
from app.embeddings.qdrant_client import upsert_embedding
from app.images.models import ImageStatus
from app.images.repository import ImageRepository
from app.shared import storage

THUMBNAIL_SIZE = (400, 400)


@celery_app.task(name="processing.thumbnail")
def thumbnail_task(image_id: str) -> str:
    asyncio.run(_thumbnail(uuid.UUID(image_id)))
    return image_id


async def _thumbnail(image_id: uuid.UUID) -> None:
    async with task_db_session() as session:
        repository = ImageRepository(session)
        image = await repository.get_by_id(image_id)

        original = await storage.download_bytes(image.storage_path)
        with PILImage.open(BytesIO(original)) as img:
            width, height = img.size
            img.thumbnail(THUMBNAIL_SIZE)
            buffer = BytesIO()
            img.convert("RGB").save(buffer, format="JPEG")

        thumbnail_path = f"thumbnails/{image.owner_id}/{image.id}.jpg"
        await storage.upload_bytes(thumbnail_path, buffer.getvalue(), "image/jpeg")

        await repository.update(
            image,
            thumbnail_path=thumbnail_path,
            width=width,
            height=height,
            status=ImageStatus.PROCESSING,
        )


@celery_app.task(name="processing.embedding")
def embedding_task(image_id: str) -> str:
    asyncio.run(_embedding(uuid.UUID(image_id)))
    return image_id


async def _embedding(image_id: uuid.UUID) -> None:
    async with task_db_session() as session:
        repository = ImageRepository(session)
        image = await repository.get_by_id(image_id)

        original = await storage.download_bytes(image.storage_path)
        with PILImage.open(BytesIO(original)) as img:
            vector = encode_image(img.convert("RGB"))

        await upsert_embedding(image.id, image.owner_id, vector)


@celery_app.task(name="processing.mark_completed")
def mark_completed_task(image_id: str) -> None:
    asyncio.run(_mark_completed(uuid.UUID(image_id)))


async def _mark_completed(image_id: uuid.UUID) -> None:
    async with task_db_session() as session:
        repository = ImageRepository(session)
        image = await repository.get_by_id(image_id)
        await repository.update(image, status=ImageStatus.COMPLETED)


@celery_app.task(name="processing.mark_failed")
def mark_failed_task(request, exc, traceback, image_id: str) -> None:
    asyncio.run(_mark_failed(uuid.UUID(image_id)))


async def _mark_failed(image_id: uuid.UUID) -> None:
    async with task_db_session() as session:
        repository = ImageRepository(session)
        image = await repository.get_by_id(image_id)
        if image is not None:
            await repository.update(image, status=ImageStatus.FAILED)
