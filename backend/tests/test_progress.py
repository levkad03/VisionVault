import json
import uuid
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.processing import progress


def test_get_redis_singleton(monkeypatch):
    monkeypatch.setattr(progress, "_redis", None)
    fake_client = object()

    with patch(
        "app.processing.progress.redis.from_url", return_value=fake_client
    ) as mock_from_url:
        first = progress.get_redis()
        second = progress.get_redis()

    assert first is fake_client
    assert second is fake_client
    mock_from_url.assert_called_once()


def test_get_redis_uses_celery_broker_url(monkeypatch):
    monkeypatch.setattr(progress, "_redis", None)
    with patch("app.processing.progress.redis.from_url") as mock_from_url:
        progress.get_redis()

    mock_from_url.assert_called_once_with(settings.celery_broker_url)


async def test_publish_stage_publishes_to_owner_channel():
    owner_id = uuid.uuid4()
    image_id = uuid.uuid4()
    mock_redis = AsyncMock()

    with patch("app.processing.progress.get_redis", return_value=mock_redis):
        await progress.publish_stage(owner_id, image_id, "thumbnail", "processing")

    mock_redis.publish.assert_awaited_once()
    channel, body = mock_redis.publish.await_args.args
    assert channel == f"ws:user:{owner_id}"
    assert json.loads(body) == {
        "image_id": str(image_id),
        "stage": "thumbnail",
        "status": "processing",
    }
