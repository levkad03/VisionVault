from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

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

    async def list_images(
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

    async def status_counts(self, owner_id: uuid.UUID) -> dict[ImageStatus, int]:
        result = await self.session.execute(
            select(Image.status, func.count(Image.id))
            .where(Image.owner_id == owner_id)
            .group_by(Image.status)
        )

        return dict(result.tuples().all())

    async def mime_type_counts(self, owner_id: uuid.UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(Image.mime_type, func.count(Image.id))
            .where(Image.owner_id == owner_id)
            .group_by(Image.mime_type)
        )

        return dict(result.tuples().all())

    async def uploads_per_day(
        self, owner_id: uuid.UUID, days: int = 30
    ) -> list[tuple[date, int]]:
        since = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(func.date(Image.uploaded_at), func.count(Image.id))
            .where(Image.owner_id == owner_id, Image.uploaded_at >= since)
            .group_by(func.date(Image.uploaded_at))
            .order_by(func.date(Image.uploaded_at))
        )

        return list(result.tuples().all())

    async def stats(self, owner_id: uuid.UUID) -> tuple[int, int]:
        result = await self.session.execute(
            select(
                func.count(Image.id), func.coalesce(func.sum(Image.size_bytes), 0)
            ).where(Image.owner_id == owner_id)
        )

        count, storage_bytes = result.one()

        return count, storage_bytes
