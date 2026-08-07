import uuid

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OCRResult(Base):
    __tablename__ = "ocr_result"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("image.id", ondelete="cascade"), nullable=False, index=True
    )

    text: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
