import uuid

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Caption(Base):
    __tablename__ = "caption"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("image.id", ondelete="cascade"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
