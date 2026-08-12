import uuid

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class DetectedObject(Base):
    __tablename__ = "detected_object"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("image.id", ondelete="cascade"), nullable=False, index=True
    )

    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_box: Mapped[list[float]] = mapped_column(JSON, nullable=False)
