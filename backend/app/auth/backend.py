import uuid

from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from app.auth.manager import get_user_manager
from app.auth.models import User
from app.core.config import settings

bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.jwt_secret, lifetime_seconds=settings.jwt_lifetime_seconds
    )


def get_refresh_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.refresh_token_secret,
        lifetime_seconds=settings.refresh_token_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_active_user = fastapi_users.current_user(active=True)
