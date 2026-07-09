from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.auth.backend import fastapi_users, get_jwt_strategy, get_refresh_strategy
from app.auth.manager import UserManager, get_user_manager
from app.auth.schemas import UserCreate, UserRead, UserUpdate

router = APIRouter()

router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenPair)
async def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
) -> TokenPair:
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
        )

    access_token = await get_jwt_strategy().write_token(user)
    refresh_token = await get_refresh_strategy().write_token(user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    user_manager: UserManager = Depends(get_user_manager),
) -> TokenPair:
    user = await get_refresh_strategy().read_token(body.refresh_token, user_manager)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    access_token = await get_jwt_strategy().write_token(user)
    new_refresh_token = await get_refresh_strategy().write_token(user)
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)
