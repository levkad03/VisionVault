import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.auth.models import User
from app.captions.repository import CaptionRepository
from app.captions.schemas import CaptionRead
from app.captions.service import CaptionService
from app.core.database import get_db
from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> CaptionService:
    return CaptionService(CaptionRepository(session), ImageRepository(session))


@router.get("/{image_id}/caption", response_model=CaptionRead | None)
async def get_caption(
    image_id: uuid.UUID,
    user: User = Depends(current_active_user),
    service: CaptionService = Depends(get_service),
) -> CaptionRead | None:
    try:
        caption = await service.get(user.id, image_id)
    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc

    if caption is None:
        return None

    return CaptionRead(id=caption.id, text=caption.text, model=caption.model)
