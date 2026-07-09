from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api import router as auth_router
from app.core.config import settings
from app.core.database import get_db
from app.images.api import router as images_router
from app.shared.storage import ensure_bucket_exists


async def lifespan(app: FastAPI):
    await ensure_bucket_exists()
    yield


app = FastAPI(title="VisionVault API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(images_router, prefix="/images", tags=["images"])


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
