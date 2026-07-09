from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import current_active_user
from app.auth.models import User
from app.core.database import get_db
from app.images.api import to_read
from app.images.repository import ImageRepository
from app.search.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.search.service import SearchService

router = APIRouter()


def get_service(session: AsyncSession = Depends(get_db)) -> SearchService:
    return SearchService(ImageRepository(session))


@router.post("", response_model=SearchResponse)
async def search_images(
    body: SearchRequest,
    user: User = Depends(current_active_user),
    service: SearchService = Depends(get_service),
) -> SearchResponse:
    results = await service.search(user.id, body.query, body.limit, body.offset)
    items = [
        SearchResultItem(**(await to_read(image)).model_dump(), score=score)
        for image, score in results
    ]

    return SearchResponse(items=items, limit=body.limit, offset=body.offset)
