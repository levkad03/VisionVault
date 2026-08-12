import uuid

from pydantic import BaseModel


class OCRResultRead(BaseModel):
    id: uuid.UUID
    text: str
    language: str | None
    confidence: float
