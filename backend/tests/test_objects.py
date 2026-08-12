import uuid

import pytest

from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.images.exceptions import ImageNotFound
from app.images.models import ImageStatus
from app.images.repository import ImageRepository
from app.objects.repository import ObjectRepository
from app.objects.service import ObjectService


@pytest.fixture
def service(session):
    return ObjectService(ObjectRepository(session), ImageRepository(session))


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


DETECTION = {
    "class_name": "cat",
    "confidence": 0.92,
    "bounding_box": [1.0, 2.0, 3.0, 4.0],
}


async def _auth_headers(client):
    await client.post(
        "/auth/register", json={"email": "obj@example.com", "password": "pw123456"}
    )

    tokens = (
        await client.post(
            "/auth/login",
            data={"username": "obj@example.com", "password": "pw123456"},
        )
    ).json()

    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_create_many_persists_detections(session, user):
    image = await _create_image(session, user.id)
    repo = ObjectRepository(session)

    created = await repo.create_many(image.id, [DETECTION, DETECTION])

    assert len(created) == 2
    assert created[0].class_name == "cat"
    assert created[0].confidence == 0.92
    assert created[0].bounding_box == [1.0, 2.0, 3.0, 4.0]


async def test_list_by_image_scoped_to_image(session, user):
    image_a = await _create_image(session, user.id, filename="a.jpg")
    image_b = await _create_image(session, user.id, filename="b.jpg")
    repo = ObjectRepository(session)

    await repo.create_many(image_a.id, [DETECTION])
    await repo.create_many(image_b.id, [DETECTION, DETECTION])

    result = await repo.list_by_image(image_a.id)
    assert len(result) == 1


async def test_list_by_image_empty_when_none(session, user):
    image = await _create_image(session, user.id)
    repo = ObjectRepository(session)

    assert await repo.list_by_image(image.id) == []


async def test_list_objects_returns_own_detections(service, session, user):
    image = await _create_image(session, user.id)
    await ObjectRepository(session).create_many(image.id, [DETECTION])

    result = await service.list_objects(user.id, image.id)
    assert len(result) == 1


async def test_list_objects_raises_for_other_owner(service, session, user, other_user):
    image = await _create_image(session, user.id)
    with pytest.raises(ImageNotFound):
        await service.list_objects(other_user.id, image.id)


async def test_list_objects_raises_for_missing_image(service, user):
    with pytest.raises(ImageNotFound):
        await service.list_objects(user.id, uuid.uuid4())


async def test_list_objects_404_for_missing_image(client):
    headers = await _auth_headers(client)
    r = await client.get(f"/images/{uuid.uuid4()}/objects", headers=headers)
    assert r.status_code == 404


async def test_list_objects_404_for_foreign_image(client, session, user):
    image = await _create_image(session, user.id)
    headers = await _auth_headers(client)
    r = await client.get(f"/images/{image.id}/objects", headers=headers)
    assert r.status_code == 404


async def test_list_objects_returns_detections_via_api(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    image = await _create_image(session, uuid.UUID(me["id"]))
    await ObjectRepository(session).create_many(image.id, [DETECTION])

    r = await client.get(f"/images/{image.id}/objects", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["class_name"] == "cat"
    assert body[0]["bounding_box"] == [1.0, 2.0, 3.0, 4.0]


async def test_list_returns_empty_list_via_api(client, session):
    headers = await _auth_headers(client)
    me = (await client.get("/auth/me", headers=headers)).json()
    image = await _create_image(session, uuid.UUID(me["id"]))

    r = await client.get(f"/images/{image.id}/objects", headers=headers)
    assert r.status_code == 200
    assert r.json() == []
