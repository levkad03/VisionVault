import uuid

from pydantic import BaseModel


class CaptionRead(BaseModel):
    id: uuid.UUID
    text: str
    model: str
