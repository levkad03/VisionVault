from pydantic import BaseModel, Field

from app.images.schemas import ImageRead


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(20, le=100)
    offset: int = Field(0, ge=0)


class SearchResultItem(ImageRead):
    score: float


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    limit: int
    offset: int
