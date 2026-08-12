import uuid

from pydantic import BaseModel


class DetectedObjectRead(BaseModel):
    id: uuid.UUID
    class_name: str
    confidence: float
    bounding_box: list[float]
