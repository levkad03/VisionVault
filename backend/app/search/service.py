import uuid

from starlette.concurrency import run_in_threadpool

from app.embeddings import qdrant_client
from app.embeddings.clip import encode_text
from app.images.models import Image
from app.images.repository import ImageRepository


class SearchService:
    def __init__(self, repository: ImageRepository):
        self.repository = repository

    async def search(
        self, owner_id: uuid.UUID, query: str, limit: int, offset: int
    ) -> list[tuple[Image, float]]:
        vector = await run_in_threadpool(encode_text, query)
        hits = await qdrant_client.search(owner_id, vector, limit, offset)
        if not hits:
            return []

        ids = [image_id for image_id, _ in hits]
        images = await self.repository.get_by_ids(owner_id, ids)
        images_by_id = {image.id: image for image in images}

        return [
            (images_by_id[image_id], score)
            for image_id, score in hits
            if image_id in images_by_id
        ]
