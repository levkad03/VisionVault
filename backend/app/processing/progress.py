import json
import uuid

import redis.asyncio as redis

from app.core.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis

    if _redis is None:
        _redis = redis.from_url(settings.celery_broker_url)

    return _redis


async def publish_stage(
    owner_id: uuid.UUID, image_id: uuid.UUID, stage: str, status: str
) -> None:
    message = json.dumps({"image_id": str(image_id), "stage": stage, "status": status})
    await get_redis().publish(f"ws:user:{owner_id}", message)
