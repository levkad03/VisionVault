import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.objects.models import DetectedObject


class ObjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_image(self, image_id: uuid.UUID) -> list[DetectedObject]:
        result = await self.session.execute(
            select(DetectedObject).where(DetectedObject.image_id == image_id)
        )

        return list(result.scalars().all())
