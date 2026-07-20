import uuid

from celery import chain
from fastapi import UploadFile

from app.core.config import settings
from app.embeddings.qdrant_client import delete_embedding
from app.images.exceptions import FileTooLarge, ImageNotFound, InvalidFileType
from app.images.models import Image, ImageStatus
from app.images.repository import ImageRepository
from app.processing.tasks import (
    embedding_task,
    mark_completed_task,
    mark_failed_task,
    thumbnail_task,
)
from app.shared import storage


class ImageService:
    def __init__(self, repository: ImageRepository):
        self.repository = repository

    async def upload(self, owner_id: uuid.UUID, file: UploadFile) -> Image:
        if file.content_type not in settings.upload_allowed_mime_types_list:
            raise InvalidFileType(file.content_type)

        contents = await file.read()
        size_mb = len(contents) / (1024 * 1024)
        if size_mb > settings.upload_max_size_mb:
            raise FileTooLarge(round(size_mb, 1))

        object_name = f"{owner_id}/{uuid.uuid4()}_{file.filename}"
        await storage.upload_bytes(object_name, contents, file.content_type)

        image = await self.repository.create(
            owner_id=owner_id,
            filename=file.filename,
            storage_path=object_name,
            mime_type=file.content_type,
            size_bytes=len(contents),
            status=ImageStatus.PENDING,
        )

        pipeline = chain(
            thumbnail_task.s(str(image.id)),
            embedding_task.s(),
            mark_completed_task.s(),
        )
        pipeline.apply_async(link_error=mark_failed_task.s(str(image.id)))

        return image

    async def get(self, owner_id: uuid.UUID, image_id: uuid.UUID) -> Image:
        image = await self.repository.get(image_id, owner_id)
        if image is None:
            raise ImageNotFound(image_id)

        return image

    async def list(
        self,
        owner_id: uuid.UUID,
        limit: int,
        offset: int,
        status_filter: ImageStatus | None,
    ) -> tuple[list[Image], int]:
        return await self.repository.list(owner_id, limit, offset, status_filter)

    async def delete(self, owner_id: uuid.UUID, image_id: uuid.UUID) -> None:
        image = await self.get(owner_id, image_id)
        await storage.delete_object(image.storage_path)
        if image.thumbnail_path:
            await storage.delete_object(image.thumbnail_path)
        await delete_embedding(image.id)

        await self.repository.delete(image)
