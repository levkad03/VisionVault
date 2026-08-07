import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.captions.models import Caption


class CaptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_image(self, image_id: uuid.UUID) -> Caption | None:
        result = await self.session.execute(
            select(Caption).where(Caption.image_id == image_id)
        )

        return result.scalar_one_or_none()
