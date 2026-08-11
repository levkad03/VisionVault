from fastapi import APIRouter, WebSocket, status
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from app.auth.backend import get_jwt_strategy
from app.auth.manager import UserManager
from app.auth.models import User
from app.core.database import async_session_factory
from app.processing.progress import get_redis

router = APIRouter()


@router.websocket("/ws/images")
async def images_ws(websocket: WebSocket, token: str) -> None:
    strategy = get_jwt_strategy()

    async with async_session_factory() as session:
        user_manager = UserManager(SQLAlchemyUserDatabase(session, User))
        user = await strategy.read_token(token, user_manager)

    if user is None or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(f"ws:user:{user.id}")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"].decode())

    finally:
        await pubsub.unsubscribe(f"ws:user:{user.id}")
        await pubsub.close()
