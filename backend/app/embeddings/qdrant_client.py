import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings

client = AsyncQdrantClient(url=settings.qdrant_url)


async def ensure_collection_exists() -> None:
    exists = await client.collection_exists(settings.qdrant_collection_name)
    if not exists:
        await client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        )


async def upsert_embedding(
    image_id: uuid.UUID, owner_id: uuid.UUID, vector: list[float]
) -> None:
    await client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=[
            PointStruct(
                id=str(image_id),
                vector=vector,
                payload={"image_id": str(image_id), "owner_id": str(owner_id)},
            )
        ],
    )


async def delete_embedding(image_id: uuid.UUID) -> None:
    await client.delete(
        collection_name=settings.qdrant_collection_name,
        points_selector=[str(image_id)],
    )


async def search(
    owner_id: uuid.UUID, vector: list[float], limit: int, offset: int
) -> list[tuple[uuid.UUID, float]]:
    response = await client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=vector,
        query_filter=Filter(
            must=[FieldCondition(key="owner_id", match=MatchValue(value=str(owner_id)))]
        ),
        limit=limit,
        offset=offset,
    )
    return [
        (uuid.UUID(point.payload["image_id"]), point.score) for point in response.points
    ]
