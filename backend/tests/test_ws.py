import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from fastapi import status

from app.auth.backend import get_jwt_strategy
from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate
from app.processing.ws import images_ws


async def _create_user(session, email):
    user_db = await anext(get_user_db(session))
    manager = await anext(get_user_manager(user_db))

    return await manager.create(UserCreate(email=email, password="pw123456"))


@pytest.fixture
async def user(session):
    return await _create_user(session, f"{uuid.uuid4()}@example.com")


@asynccontextmanager
async def _reuse_session(session):
    yield session


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.closed_code = None
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def close(self, code):
        self.closed_code = code

    async def send_text(self, data):
        self.sent.append(data)


class FakePubSub:
    def __init__(self, messages=None, subscribe_error=None):
        self._messages = messages or []
        self._subscribe_error = subscribe_error
        self.subscribed = None
        self.unsubscribed = None
        self.closed = False

    async def subscribe(self, channel):
        if self._subscribe_error:
            raise self._subscribe_error
        self.subscribed = channel

    async def listen(self):
        for m in self._messages:
            yield m

    async def unsubscribe(self, channel):
        self.unsubscribed = channel

    async def close(self):
        self.closed = True


class FakeRedis:
    def __init__(self, pubsub):
        self._pubsub = pubsub

    def pubsub(self):
        return self._pubsub


async def test_rejects_malformed_token(session):
    ws = FakeWebSocket()

    with patch(
        "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
    ):
        await images_ws(ws, "garbage_token")

    assert ws.accepted is False
    assert ws.closed_code == status.WS_1008_POLICY_VIOLATION


async def test_rejects_inactive_user(session, user):
    user.is_active = False
    await session.flush()
    token = await get_jwt_strategy().write_token(user)
    ws = FakeWebSocket()

    with patch(
        "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
    ):
        await images_ws(ws, token)

    assert ws.accepted is False
    assert ws.closed_code == status.WS_1008_POLICY_VIOLATION


async def test_accepts_and_forwards_only_message_events(session, user):
    token = await get_jwt_strategy().write_token(user)
    ws = FakeWebSocket()
    pubsub = FakePubSub(
        messages=[
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": b'{"stage": "thumbnail"}'},
            {"type": "message", "data": b'{"stage": "done"}'},
        ]
    )

    with (
        patch(
            "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
        ),
        patch("app.processing.ws.get_redis", return_value=FakeRedis(pubsub)),
    ):
        await images_ws(ws, token)

    assert ws.accepted is True
    assert ws.sent == ['{"stage": "thumbnail"}', '{"stage": "done"}']
    assert pubsub.subscribed == f"ws:user:{user.id}"


async def test_cleans_up_pubsub_on_normal_completion(session, user):
    token = await get_jwt_strategy().write_token(user)
    ws = FakeWebSocket()
    pubsub = FakePubSub(messages=[])

    with (
        patch(
            "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
        ),
        patch("app.processing.ws.get_redis", return_value=FakeRedis(pubsub)),
    ):
        await images_ws(ws, token)

    assert pubsub.unsubscribed == f"ws:user:{user.id}"
    assert pubsub.closed is True


async def test_cleans_up_pubsub_on_send_failure(session, user):
    token = await get_jwt_strategy().write_token(user)
    ws = FakeWebSocket()
    pubsub = FakePubSub(
        messages=[
            {"type": "message", "data": b"first"},
            {"type": "message", "data": b"second"},
        ]
    )

    calls = 0

    async def flaky_send_text(data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("client disconnected")
        ws.sent.append(data)

    ws.send_text = flaky_send_text

    with (
        patch(
            "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
        ),
        patch("app.processing.ws.get_redis", return_value=FakeRedis(pubsub)),
        pytest.raises(RuntimeError),
    ):
        await images_ws(ws, token)

    assert pubsub.closed is True


async def test_cleans_up_pubsub_when_subscribe_fails(session, user):
    token = await get_jwt_strategy().write_token(user)
    ws = FakeWebSocket()
    pubsub = FakePubSub(subscribe_error=RuntimeError("redis down"))

    with (
        patch(
            "app.processing.ws.async_session_factory", lambda: _reuse_session(session)
        ),
        patch("app.processing.ws.get_redis", return_value=FakeRedis(pubsub)),
        pytest.raises(RuntimeError),
    ):
        await images_ws(ws, token)

    assert pubsub.closed is True
