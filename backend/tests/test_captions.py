import uuid

import pytest

from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.captions.repository import CaptionRepository
from app.captions.service import CaptionService
from app.images.exceptions import ImageNotFound
from app.images.models import ImageStatus
from app.images.repository import ImageRepository


@pytest.fixture
def service(session):
    return CaptionService(CaptionRepository(session), ImageRepository(session))


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


async def _auth_headers(client):
    await client.post(
        "/auth/register", json={"email": "cap@example.com", "password": "pw123456"}
    )
    tokens = (
        await client.post(
            "/auth/login",
            data={"username": "cap@example.com", "password": "pw123456"},
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_create_persists_caption(session, user):
    image = await _create_image(session, user.id)
    repo = CaptionRepository(session)

    caption = await repo.create(image.id, "a cat on a couch", "blip-base")

    assert caption.text == "a cat on a couch"
    assert caption.model == "blip-base"


async def test_get_by_image_returns_none_when_missing(session, user):
    image = await _create_image(session, user.id)
    repo = CaptionRepository(session)

    assert await repo.get_by_image(image.id) is None


async def test_get_by_image_scoped_to_image(session, user):
    image_a = await _create_image(session, user.id, filename="a.jpg")
    image_b = await _create_image(session, user.id, filename="b.jpg")
    repo = CaptionRepository(session)

    await repo.create(image_a.id, "caption a", "blip-base")

    assert await repo.get_by_image(image_a.id) is not None
    assert await repo.get_by_image(image_b.id) is None


async def test_get_returns_own_caption(service, session, user):
    image = await _create_image(session, user.id)
    await CaptionRepository(session).create(image.id, "a dog", "blip-base")

    result = await service.get(user.id, image.id)
    assert result.text == "a dog"


async def test_get_returns_none_when_no_caption_yet(service, session, user):
    image = await _create_image(session, user.id)
    assert await service.get(user.id, image.id) is None


async def test_get_raises_for_other_owner(service, session, user, other_user):
    image = await _create_image(session, user.id)
    with pytest.raises(ImageNotFound):
        await service.get(other_user.id, image.id)


async def test_get_raises_for_missing_image(service, user):
    with pytest.raises(ImageNotFound):
        await service.get(user.id, uuid.uuid4())


async def test_get_caption_404_for_missing_image(client):
    headers = await _auth_headers(client)
    r = await client.get(f"/images/{uuid.uuid4()}/caption", headers=headers)
    assert r.status_code == 404


async def test_get_caption_404_for_foreign_image(client, session, user):
    image = await _create_image(session, user.id)
    headers = await _auth_headers(client)  # different account than `user` fixture
    r = await client.get(f"/images/{image.id}/caption", headers=headers)
    assert r.status_code == 404


async def test_get_caption_returns_caption_via_api(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    image = await _create_image(session, uuid.UUID(me["id"]))
    await CaptionRepository(session).create(image.id, "a sunset", "blip-base")

    r = await client.get(f"/images/{image.id}/caption", headers=headers)
    assert r.status_code == 200
    assert r.json()["text"] == "a sunset"


async def test_get_caption_returns_null_when_none_yet(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    image = await _create_image(session, uuid.UUID(me["id"]))

    r = await client.get(f"/images/{image.id}/caption", headers=headers)
    assert r.status_code == 200
    assert r.json() is None
