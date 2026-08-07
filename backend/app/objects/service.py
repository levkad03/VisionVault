import uuid

from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository
from app.objects.models import DetectedObject
from app.objects.repository import ObjectRepository


class ObjectService:
    def __init__(self, repository: ObjectRepository, image_repository: ImageRepository):
        self.repository = repository
        self.image_repository = image_repository

    async def list_objects(
        self, owner_id: uuid.UUID, image_id: uuid.UUID
    ) -> list[DetectedObject]:
        image = await self.image_repository.get(image_id, owner_id)
        if image is None:
            raise ImageNotFound(image_id)

        return await self.repository.list_by_image(image_id)
