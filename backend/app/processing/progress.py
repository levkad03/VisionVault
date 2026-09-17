import json
import uuid

import redis.asyncio as redis

from app.core.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Shared client for the FastAPI process (single long-lived event loop)."""
    global _redis

    if _redis is None:
        _redis = redis.from_url(settings.celery_broker_url)

    return _redis


async def publish_stage(
    owner_id: uuid.UUID, image_id: uuid.UUID, stage: str, status: str
) -> None:
    message = json.dumps({"image_id": str(image_id), "stage": stage, "status": status})
    async with redis.from_url(settings.celery_broker_url) as client:
        await client.publish(f"ws:user:{owner_id}", message)
