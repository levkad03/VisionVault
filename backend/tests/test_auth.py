from app.auth.manager import get_user_db, get_user_manager
from app.auth.schemas import UserCreate


async def _register(client, email="user@example.com", password="pw123456"):
    return await client.post(
        "/auth/register", json={"email": email, "password": password}
    )


async def _login(client, email="user@example.com", password="pw123456"):
    return await client.post(
        "/auth/login", data={"username": email, "password": password}
    )


async def test_register_success(client):
    r = await _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "user@example.com"
    assert "hashed_password" not in body


async def test_register_duplicate_email_rejected(client):
    await _register(client)
    r = await _register(client)
    assert r.status_code == 400
    assert r.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"


async def test_login_success(client):
    await _register(client)
    r = await _login(client)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await _register(client)
    r = await _login(client, password="wrongpass")
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid credentials"


async def test_login_nonexistent_user(client):
    r = await _login(client, email="ghost@example.com")
    assert r.status_code == 400


async def test_login_inactive_user_rejected(client, session):
    user_db = anext(get_user_db(session))
    user_db = await user_db
    manager = await anext(get_user_manager(user_db))
    user = await manager.create(
        UserCreate(email="inactive@example.com", password="pw123456")
    )
    await manager.user_db.update(user, {"is_active": False})

    r = await _login(client, email="inactive@example.com")
    assert r.status_code == 400


async def test_refresh_success(client):
    await _register(client)
    tokens = (await _login(client)).json()

    r = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 200
    new_tokens = r.json()

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


async def test_refresh_invalid_token_rejected(client):
    r = await client.post("/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


async def test_refresh_rejects_access_token_used_as_refresh(client):
    await _register(client)
    tokens = (await _login(client)).json()

    r = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert r.status_code == 401


async def test_me_rejects_missing_token(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_rejects_invalid_token(client):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_me_returns_current_user(client):
    await _register(client)
    tokens = (await _login(client)).json()

    r = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"
