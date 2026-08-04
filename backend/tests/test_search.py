import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.images.models import ImageStatus
from app.images.repository import ImageRepository
from app.search.service import SearchService


@pytest.fixture
def service(session):
    return SearchService(ImageRepository(session))


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
        status=ImageStatus.COMPLETED,
    )
    fields.update(overrides)
    return await ImageRepository(session).create(**fields)


async def test_search_hydrates_qdrant_hits_in_score_order(service, session, user):
    image_a = await _create_image(session, user.id, filename="a.jpg")
    image_b = await _create_image(session, user.id, filename="b.jpg")

    with (
        patch("app.search.service.encode_text", return_value=[0.1] * 512),
        patch(
            "app.search.service.qdrant_client.search",
            new=AsyncMock(return_value=[(image_b.id, 0.92), (image_a.id, 0.71)]),
        ),
    ):
        results = await service.search(user.id, "a dog on a beach", limit=10, offset=0)

    assert results == [(image_b, 0.92), (image_a, 0.71)]


async def test_search_skips_hits_missing_from_db(service, session, user):
    image = await _create_image(session, user.id)
    deleted_id = uuid.uuid4()

    with (
        patch("app.search.service.encode_text", return_value=[0.1] * 512),
        patch(
            "app.search.service.qdrant_client.search",
            new=AsyncMock(return_value=[(deleted_id, 0.95), (image.id, 0.8)]),
        ),
    ):
        results = await service.search(user.id, "query", limit=10, offset=0)

    assert results == [(image, 0.8)]


async def test_search_returns_empty_when_no_qdrant_hits(service, user):
    with (
        patch("app.search.service.encode_text", return_value=[0.1] * 512),
        patch(
            "app.search.service.qdrant_client.search", new=AsyncMock(return_value=[])
        ) as mock_search,
        patch.object(service.repository, "get_by_ids", new=AsyncMock()) as mock_get_by_ids,
    ):
        results = await service.search(user.id, "query", limit=10, offset=0)

    assert results == []
    mock_search.assert_awaited_once()
    mock_get_by_ids.assert_not_called()


async def test_search_passes_query_vector_and_pagination_to_qdrant(service, user):
    vector = [0.5] * 512
    with (
        patch("app.search.service.encode_text", return_value=vector) as mock_encode,
        patch(
            "app.search.service.qdrant_client.search", new=AsyncMock(return_value=[])
        ) as mock_search,
    ):
        await service.search(user.id, "a red car", limit=5, offset=10)

    mock_encode.assert_called_once_with("a red car")
    mock_search.assert_awaited_once_with(user.id, vector, 5, 10)


async def test_search_scopes_hits_to_requesting_owner(service, session, user):
    other_user = await _create_user(session, f"{uuid.uuid4()}@example.com")
    other_image = await _create_image(session, other_user.id)

    with (
        patch("app.search.service.encode_text", return_value=[0.1] * 512),
        patch(
            "app.search.service.qdrant_client.search",
            new=AsyncMock(return_value=[(other_image.id, 0.9)]),
        ),
    ):
        results = await service.search(user.id, "query", limit=10, offset=0)

    assert results == []


async def test_search_endpoint_rejects_missing_token(client):
    r = await client.post("/search", json={"query": "a dog"})
    assert r.status_code == 401


async def test_search_endpoint_returns_scored_results(client, session):
    await client.post(
        "/auth/register", json={"email": "search@example.com", "password": "pw123456"}
    )
    tokens = (
        await client.post(
            "/auth/login",
            data={"username": "search@example.com", "password": "pw123456"},
        )
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = (await client.get("/auth/me", headers=headers)).json()

    image = await _create_image(session, uuid.UUID(me["id"]), filename="cat.jpg")

    with (
        patch("app.search.service.encode_text", return_value=[0.1] * 512),
        patch(
            "app.search.service.qdrant_client.search",
            new=AsyncMock(return_value=[(image.id, 0.88)]),
        ),
    ):
        r = await client.post("/search", headers=headers, json={"query": "a cat"})

    assert r.status_code == 200
    body = r.json()
    assert body["items"][0]["filename"] == "cat.jpg"
    assert body["items"][0]["score"] == 0.88
