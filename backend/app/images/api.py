import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.auth.models import User
from app.captions.repository import CaptionRepository
from app.captions.schemas import CaptionRead
from app.core.database import get_db
from app.images.exceptions import FileTooLarge, ImageNotFound, InvalidFileType
from app.images.models import Image, ImageStatus
from app.images.repository import ImageRepository
from app.images.schemas import ImageDetail, ImageList, ImageRead, ImageStats
from app.images.service import ImageService
from app.objects.repository import ObjectRepository
from app.objects.schemas import DetectedObjectRead
from app.ocr.repository import OCRRepository
from app.ocr.schemas import OCRResultRead
from app.shared import storage

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> ImageService:
    return ImageService(ImageRepository(session))


async def to_read(image: Image) -> ImageRead:
    return ImageRead(
        id=image.id,
        filename=image.filename,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        uploaded_at=image.uploaded_at,
        taken_at=image.taken_at,
        camera=image.camera,
        lens=image.lens,
        gps=image.gps,
        status=image.status,
        url=await storage.get_presigned_url(image.storage_path),
        thumbnail_url=await storage.get_presigned_url(image.thumbnail_path)
        if image.thumbnail_path
        else None,
    )


async def to_detail(image: Image, session: AsyncSession) -> ImageDetail:
    base = await to_read(image)
    objects = await ObjectRepository(session).list_by_image(image.id)
    ocr_results = await OCRRepository(session).list_by_image(image.id)
    caption = await CaptionRepository(session).get_by_image(image.id)

    return ImageDetail(
        **base.model_dump(),
        dominant_colors=image.dominant_colors,
        objects=[
            DetectedObjectRead.model_validate(o, from_attributes=True) for o in objects
        ],
        ocr=[
            OCRResultRead.model_validate(o, from_attributes=True) for o in ocr_results
        ],
        caption=CaptionRead.model_validate(caption, from_attributes=True)
        if caption
        else None,
    )


@router.post("", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile,
    user: User = Depends(current_active_user),
    service: ImageService = Depends(get_service),
) -> ImageRead:
    try:
        image = await service.upload(user.id, file)
    except InvalidFileType as exc:
        raise HTTPException(
            status_code=415, detail=f"Unsupported file type: {exc}"
        ) from exc
    except FileTooLarge as exc:
        raise HTTPException(status_code=413, detail=f"File too large: {exc}MB") from exc

    return await to_read(image)


@router.get("", response_model=ImageList)
async def list_images(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    status_filter: ImageStatus | None = Query(None, alias="status"),
    user: User = Depends(current_active_user),
    service: ImageService = Depends(get_service),
) -> ImageList:
    images, total = await service.list(user.id, limit, offset, status_filter)
    return ImageList(
        items=[await to_read(i) for i in images],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=ImageStats)
async def get_stats(
    user: User = Depends(current_active_user),
    service: ImageService = Depends(get_service),
) -> ImageStats:
    return await service.stats(user.id)


@router.get("/{image_id}", response_model=ImageDetail)
async def get_image(
    image_id: uuid.UUID,
    user: User = Depends(current_active_user),
    service: ImageService = Depends(get_service),
    session: AsyncSession = Depends(get_db),
) -> ImageDetail:
    try:
        image = await service.get(user.id, image_id)
    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc

    return await to_detail(image, session)


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: uuid.UUID,
    user: User = Depends(current_active_user),
    service: ImageService = Depends(get_service),
) -> None:
    try:
        await service.delete(user.id, image_id)
    except ImageNotFound as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
