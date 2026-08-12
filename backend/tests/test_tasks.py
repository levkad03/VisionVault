import uuid
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image as PILImage

from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.captions.repository import CaptionRepository
from app.core.config import settings
from app.images.models import ImageStatus
from app.images.repository import ImageRepository
from app.objects.repository import ObjectRepository
from app.ocr.repository import OCRRepository
from app.processing import tasks


async def _create_user(session, email):
    user_db = await anext(get_user_db(session))
    manager = await anext(get_user_manager(user_db))
    return await manager.create(UserCreate(email=email, password="pw123456"))


@pytest.fixture
async def user(session):
    return await _create_user(session, f"{uuid.uuid4()}@example.com")


async def _create_image(session, owner_id, **overrides):
    fields = dict(
        owner_id=owner_id,
        filename="photo.jpg",
        storage_path="owner/photo.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        status=ImageStatus.PENDING,
    )
    fields.update(overrides)
    return await ImageRepository(session).create(**fields)


def _fake_image_bytes():
    buf = BytesIO()
    PILImage.new("RGB", (20, 20), color=(255, 0, 0)).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _use_test_db(session, monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _reuse_session():
        yield session

    monkeypatch.setattr(tasks, "task_db_session", _reuse_session)


async def test_thumbnail_updates_image_and_publishes(session, user):
    image = await _create_image(session, user.id)

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch(
            "app.processing.tasks.storage.upload_bytes", new=AsyncMock()
        ) as mock_upload,
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._thumbnail(image.id)

    updated = await ImageRepository(session).get_by_id(image.id)
    assert updated.width == 20
    assert updated.height == 20
    assert updated.status == ImageStatus.PROCESSING
    assert updated.thumbnail_path == f"thumbnails/{user.id}/{image.id}.jpg"
    mock_upload.assert_awaited_once()
    mock_publish.assert_awaited_once_with(user.id, image.id, "thumbnail", "processing")


async def test_thumbnail_noop_when_image_missing():
    with (
        patch(
            "app.processing.tasks.storage.download_bytes", new=AsyncMock()
        ) as mock_dl,
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._thumbnail(uuid.uuid4())

    mock_dl.assert_not_awaited()
    mock_publish.assert_not_awaited()


async def test_embedding_upserts_vector_and_publishes(session, user):
    image = await _create_image(session, user.id)
    vector = [0.1, 0.2, 0.3]

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.encode_image", return_value=vector),
        patch("app.processing.tasks.upsert_embedding", new=AsyncMock()) as mock_upsert,
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._embedding(image.id)

    mock_upsert.assert_awaited_once_with(image.id, user.id, vector)
    mock_publish.assert_awaited_once_with(user.id, image.id, "embedding", "processing")


async def test_embedding_noop_when_image_missing():
    with (
        patch("app.processing.tasks.upsert_embedding", new=AsyncMock()) as mock_upsert,
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._embedding(uuid.uuid4())

    mock_upsert.assert_not_awaited()
    mock_publish.assert_not_awaited()


async def test_metadata_updates_image_and_publishes(session, user):
    image = await _create_image(session, user.id)
    meta = {"taken_at": None, "camera": "Canon X", "lens": None, "gps": None}

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.extract_metadata", return_value=meta),
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._metadata(image.id)

    updated = await ImageRepository(session).get_by_id(image.id)
    assert updated.camera == "Canon X"
    mock_publish.assert_awaited_once_with(user.id, image.id, "metadata", "processing")


async def test_metadata_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._metadata(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_color_updates_image_and_publishes(session, user):
    image = await _create_image(session, user.id)

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.extract_colors", return_value=["#ff0000"]),
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._color(image.id)

    updated = await ImageRepository(session).get_by_id(image.id)
    assert updated.dominant_colors == ["#ff0000"]
    mock_publish.assert_awaited_once_with(user.id, image.id, "color", "processing")


async def test_color_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._color(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_object_detection_persists_detections_and_publishes(session, user):
    image = await _create_image(session, user.id)
    detections = [
        {"class_name": "cat", "confidence": 0.9, "bounding_box": [1.0, 2.0, 3.0, 4.0]}
    ]

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.detect_objects", return_value=detections),
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._object_detection(image.id)

    saved = await ObjectRepository(session).list_by_image(image.id)
    assert len(saved) == 1
    assert saved[0].class_name == "cat"
    mock_publish.assert_awaited_once_with(
        user.id, image.id, "object_detection", "processing"
    )


async def test_object_detection_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._object_detection(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_ocr_persists_results_and_publishes(session, user):
    image = await _create_image(session, user.id)
    detections = [{"text": "hello", "confidence": 0.9, "language": "en"}]

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.read_text", return_value=detections),
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._ocr(image.id)

    saved = await OCRRepository(session).list_by_image(image.id)
    assert len(saved) == 1
    assert saved[0].text == "hello"
    mock_publish.assert_awaited_once_with(user.id, image.id, "ocr", "processing")


async def test_ocr_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._ocr(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_caption_persists_text_and_publishes(session, user):
    image = await _create_image(session, user.id)

    with (
        patch(
            "app.processing.tasks.storage.download_bytes",
            new=AsyncMock(return_value=_fake_image_bytes()),
        ),
        patch("app.processing.tasks.generate_caption", return_value="a red square"),
        patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish,
    ):
        await tasks._caption(image.id)

    saved = await CaptionRepository(session).get_by_image(image.id)
    assert saved.text == "a red square"
    assert saved.model == settings.caption_model_name
    mock_publish.assert_awaited_once_with(user.id, image.id, "caption", "processing")


async def test_caption_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._caption(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_mark_completed_updates_status_and_publishes(session, user):
    image = await _create_image(session, user.id)

    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._mark_completed(image.id)

    updated = await ImageRepository(session).get_by_id(image.id)
    assert updated.status == ImageStatus.COMPLETED
    mock_publish.assert_awaited_once_with(user.id, image.id, "done", "completed")


async def test_mark_completed_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._mark_completed(uuid.uuid4())

    mock_publish.assert_not_awaited()


async def test_mark_failed_updates_status_and_publishes(session, user):
    image = await _create_image(session, user.id)

    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._mark_failed(image.id)

    updated = await ImageRepository(session).get_by_id(image.id)
    assert updated.status == ImageStatus.FAILED
    mock_publish.assert_awaited_once_with(user.id, image.id, "failed", "failed")


async def test_mark_failed_noop_when_image_missing():
    with patch("app.processing.tasks.publish_stage", new=AsyncMock()) as mock_publish:
        await tasks._mark_failed(uuid.uuid4())

    mock_publish.assert_not_awaited()
