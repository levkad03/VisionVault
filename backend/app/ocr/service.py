import uuid

from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository
from app.ocr.models import OCRResult
from app.ocr.repository import OCRRepository


class OCRService:
    def __init__(self, repository: OCRRepository, image_repository: ImageRepository):
        self.repository = repository
        self.image_repository = image_repository

    async def list(self, owner_id: uuid.UUID, image_id: uuid.UUID) -> list[OCRResult]:
        image = await self.image_repository.get(image_id, owner_id)

        if image is None:
            raise ImageNotFound(image_id)

        return await self.repository.list_by_image(image_id)
