from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.images.models import Image, ImageStatus


class ImageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **fields) -> Image:
        image = Image(**fields)
        self.session.add(image)
        await self.session.commit()
        await self.session.refresh(image)
        return image

    async def get(self, image_id: uuid.UUID, owner_id: uuid.UUID) -> Image | None:
        result = await self.session.execute(
            select(Image).where(Image.id == image_id, Image.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        owner_id: uuid.UUID,
        limit: int,
        offset: int,
        status_filter: ImageStatus | None = None,
    ) -> tuple[list[Image], int]:
        query = select(Image).where(Image.owner_id == owner_id)
        if status_filter is not None:
            query = query.where(Image.status == status_filter)

        total = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )
        result = await self.session.execute(
            query.order_by(Image.uploaded_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total or 0

    async def delete(self, image: Image) -> None:
        await self.session.delete(image)
        await self.session.commit()

    async def get_by_id(self, image_id: uuid.UUID) -> Image | None:
        result = await self.session.execute(select(Image).where(Image.id == image_id))
        return result.scalar_one_or_none()

    async def update(self, image: Image, **fields) -> Image:
        for key, value in fields.items():
            setattr(image, key, value)
        await self.session.commit()
        await self.session.refresh(image)
        return image

    async def get_by_ids(
        self, owner_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[Image]:
        result = await self.session.execute(
            select(Image).where(Image.owner_id == owner_id, Image.id.in_(ids))
        )

        return list(result.scalars().all())

    async def stats(self, owner_id: uuid.UUID) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.count(Image.id), func.coalesce(func.sum(Image.size_bytes), 0)
            ).where(Image.owner_id == owner_id)
        )

        return result.one()
