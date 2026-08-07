import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.auth.models import User
from app.core.database import get_db
from app.images.exceptions import ImageNotFound
from app.images.repository import ImageRepository
from app.ocr.repository import OCRRepository
from app.ocr.schemas import OCRResultRead
from app.ocr.service import OCRService

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> OCRService:
    return OCRService(OCRRepository(session), ImageRepository(session))


@router.get("/{image_id}/ocr", response_model=list[OCRResultRead])
async def list_ocr_results(
    image_id: uuid.UUID,
    user: User = Depends(current_active_user),
    service: OCRService = Depends(get_service),
) -> list[OCRResultRead]:
    try:
        results = await service.list(user.id, image_id)

    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc

    return [
        OCRResultRead(
            id=r.id, text=r.text, language=r.language, confidence=r.confidence
        )
        for r in results
    ]
