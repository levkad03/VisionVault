import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.auth.models import User
from app.core.database import get_db
from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository
from app.objects.repository import ObjectRepository
from app.objects.schemas import DetectedObjectRead
from app.objects.service import ObjectService

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> ObjectService:
    return ObjectService(ObjectRepository(session), ImageRepository(session))


@router.get("/{image_id}/objects", response_model=list[DetectedObjectRead])
async def list_objects(
    image_id: uuid.UUID,
    user: User = Depends(current_active_user),
    service: ObjectService = Depends(get_service),
) -> list[DetectedObjectRead]:
    try:
        objects = await service.list_objects(user.id, image_id)
    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc

    return [
        DetectedObjectRead(
            id=o.id,
            class_name=o.class_name,
            confidence=o.confidence,
            bounding_box=o.bounding_box,
        )
        for o in objects
    ]
