import uuid
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import UploadFile

from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.images.exceptions import FileTooLarge, ImageNotFound, InvalidFileType
from app.images.models import ImageStatus
from app.images.repository import ImageRepository
from app.images.service import ImageService


@pytest.fixture
def service(session):
    return ImageService(ImageRepository(session))


async def _create_user(session, email):
    user_db = await anext(get_user_db(session))
    manager = await anext(get_user_manager(user_db))
    return await manager.create(UserCreate(email=email, password="pw123456"))


@pytest.fixture
async def user(session):
    return await _create_user(session, f"{uuid.uuid4()}@example.com")


@pytest.fixture
async def other_user(session):
    return await _create_user(session, f"{uuid.uuid4()}@example.com")


async def _create_image(session, owner_id, **overrides):
    fields = dict(
        owner_id=owner_id,
        filename="photo.jpg",
        storage_path="owner/photo.jpg",
        mime_type="image/jpeg",
        size_bytes=1024,
        status=ImageStatus.COMPLETED,
    )
    fields.update(overrides)
    return await ImageRepository(session).create(**fields)


def _upload_file(filename="photo.jpg", content_type="image/jpeg", data=b"x" * 100):
    return UploadFile(
        filename=filename, file=BytesIO(data), headers={"content-type": content_type}
    )


async def _auth_headers(client):
    await client.post(
        "/auth/register", json={"email": "img@example.com", "password": "pw123456"}
    )
    tokens = (
        await client.post(
            "/auth/login",
            data={"username": "img@example.com", "password": "pw123456"},
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_upload_rejects_unsupported_mime_type(service):
    with pytest.raises(InvalidFileType):
        await service.upload(uuid.uuid4(), _upload_file(content_type="text/plain"))


async def test_upload_rejects_oversized_file(service, monkeypatch):
    monkeypatch.setattr("app.images.service.settings.upload_max_size_mb", 0)
    with pytest.raises(FileTooLarge):
        await service.upload(uuid.uuid4(), _upload_file())


async def test_upload_creates_pending_row_with_size(service, user):
    with (
        patch("app.images.service.storage.upload_bytes", new=AsyncMock()),
        patch("app.images.service.chain") as mock_chain,
    ):
        mock_chain.return_value.apply_async = lambda **_: None
        image = await service.upload(user.id, _upload_file(data=b"x" * 250))

    assert image.owner_id == user.id
    assert image.status == ImageStatus.PENDING
    assert image.size_bytes == 250
    assert image.storage_path.endswith("_photo.jpg")


async def test_upload_starts_processing_pipeline(service, user):
    with (
        patch("app.images.service.storage.upload_bytes", new=AsyncMock()),
        patch("app.images.service.chain") as mock_chain,
    ):
        mock_chain.return_value.apply_async = lambda **_: None
        await service.upload(user.id, _upload_file())

    mock_chain.assert_called_once()


async def test_get_returns_own_image(service, session, user):
    image = await _create_image(session, user.id)
    fetched = await service.get(image.owner_id, image.id)
    assert fetched.id == image.id


async def test_get_raises_for_other_owner(service, session, user):
    image = await _create_image(session, user.id)
    with pytest.raises(ImageNotFound):
        await service.get(uuid.uuid4(), image.id)


async def test_get_raises_for_missing_image(service):
    with pytest.raises(ImageNotFound):
        await service.get(uuid.uuid4(), uuid.uuid4())


async def test_list_scopes_to_owner(service, session, user, other_user):
    await _create_image(session, user.id)
    await _create_image(session, user.id)
    await _create_image(session, other_user.id)

    images, total = await service.list(user.id, limit=50, offset=0, status_filter=None)
    assert total == 2
    assert {i.owner_id for i in images} == {user.id}


async def test_list_filters_by_status(service, session, user):
    await _create_image(session, user.id, status=ImageStatus.COMPLETED)
    await _create_image(session, user.id, status=ImageStatus.FAILED)

    images, total = await service.list(
        user.id, limit=50, offset=0, status_filter=ImageStatus.FAILED
    )
    assert total == 1
    assert images[0].status == ImageStatus.FAILED


async def test_list_paginates(service, session, user):
    for _ in range(3):
        await _create_image(session, user.id)

    images, total = await service.list(user.id, limit=2, offset=0, status_filter=None)
    assert total == 3
    assert len(images) == 2


async def test_delete_removes_row_and_storage(service, session, user):
    image = await _create_image(session, user.id, thumbnail_path="owner/thumb.jpg")

    with (
        patch(
            "app.images.service.storage.delete_object", new=AsyncMock()
        ) as mock_delete,
        patch(
            "app.images.service.delete_embedding", new=AsyncMock()
        ) as mock_delete_embedding,
    ):
        await service.delete(image.owner_id, image.id)

    assert mock_delete.await_count == 2  # original + thumbnail
    mock_delete_embedding.assert_awaited_once_with(image.id)
    with pytest.raises(ImageNotFound):
        await service.get(image.owner_id, image.id)


async def test_delete_raises_for_other_owner(service, session, user):
    image = await _create_image(session, user.id)
    with pytest.raises(ImageNotFound):
        await service.delete(uuid.uuid4(), image.id)


async def test_stats_counts_and_sums_owner_images_only(service, session, user, other_user):
    await _create_image(session, user.id, size_bytes=100)
    await _create_image(session, user.id, size_bytes=250)
    await _create_image(session, other_user.id, size_bytes=999)

    count, storage_bytes = await service.stats(user.id)
    assert count == 2
    assert storage_bytes == 350


async def test_stats_empty_for_new_owner(service):
    count, storage_bytes = await service.stats(uuid.uuid4())
    assert count == 0
    assert storage_bytes == 0


async def test_upload_rejects_unsupported_type_via_api(client):
    headers = await _auth_headers(client)
    r = await client.post(
        "/images", headers=headers, files={"file": ("x.txt", b"hi", "text/plain")}
    )
    assert r.status_code == 415


async def test_upload_rejects_oversized_file_via_api(client, monkeypatch):
    monkeypatch.setattr("app.images.service.settings.upload_max_size_mb", 0)
    headers = await _auth_headers(client)
    r = await client.post(
        "/images",
        headers=headers,
        files={"file": ("x.jpg", b"x" * 1024, "image/jpeg")},
    )
    assert r.status_code == 413


async def test_list_images_rejects_missing_token(client):
    r = await client.get("/images")
    assert r.status_code == 401


async def test_get_image_returns_404_for_missing_id(client):
    headers = await _auth_headers(client)
    r = await client.get(f"/images/{uuid.uuid4()}", headers=headers)
    assert r.status_code == 404


async def test_list_images_returns_owned_images_via_api(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    await _create_image(session, uuid.UUID(me["id"]), filename="a.jpg")

    r = await client.get("/images", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["filename"] == "a.jpg"
    assert body["items"][0]["url"]


async def test_stats_endpoint_returns_counts(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    await _create_image(session, uuid.UUID(me["id"]), size_bytes=500)

    r = await client.get("/images/stats", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"count": 1, "storage_bytes": 500}
