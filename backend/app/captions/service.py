import uuid

from app.captions.models import Caption
from app.captions.repository import CaptionRepository
from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository


class CaptionService:
    def __init__(
        self, repository: CaptionRepository, image_repository: ImageRepository
    ):
        self.repository = repository
        self.image_repository = image_repository

    async def get(self, owner_id: uuid.UUID, image_id: uuid.UUID) -> Caption | None:
        image = await self.image_repository.get(image_id, owner_id)

        if image is None:
            raise ImageNotFound(image_id)

        return await self.repository.get_by_image(image_id)
