import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ocr.models import OCRResult


class OCRRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_image(self, image_id: uuid.UUID) -> list[OCRResult]:
        result = await self.session.execute(
            select(OCRResult).where(OCRResult.image_id == image_id)
        )

        return list(result.scalars().all())

    async def create_many(
        self, image_id: uuid.UUID, detections: list[dict]
    ) -> list[OCRResult]:
        results = [OCRResult(image_id=image_id, **d) for d in detections]
        self.session.add_all(results)
        await self.session.commit()

        return results
