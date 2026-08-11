import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.captions.schemas import CaptionRead
from app.images.models import ImageStatus
from app.objects.schemas import DetectedObjectRead
from app.ocr.schemas import OCRResultRead


class ImageRead(BaseModel):
    id: uuid.UUID
    filename: str
    mime_type: str
    width: int | None
    height: int | None
    uploaded_at: datetime
    taken_at: datetime | None
    camera: str | None
    lens: str | None
    gps: str | None
    status: ImageStatus
    url: str
    thumbnail_url: str | None


class ImageList(BaseModel):
    items: list[ImageRead]
    total: int
    limit: int
    offset: int


class UploadsPerDay(BaseModel):
    date: date
    count: int


class ImageStats(BaseModel):
    count: int
    storage_bytes: int
    by_status: dict[ImageStatus, int]
    by_mime_type: dict[str, int]
    uploads_per_day: list[UploadsPerDay]


class ImageDetail(ImageRead):
    dominant_colors: list[str] | None
    objects: list[DetectedObjectRead]
    ocr: list[OCRResultRead]
    caption: CaptionRead | None
