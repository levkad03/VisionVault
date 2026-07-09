from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def task_db_session() -> AsyncGenerator[AsyncSession, None]:
    """DB session for Celery tasks.

    Each task runs its own asyncio.run() event loop, and asyncpg connections
    are bound to the loop that created them. Reusing the module-level
    ``engine``/``async_session_factory`` across tasks would hand out
    connections created on a loop that's already been torn down. This creates
    a throwaway engine with NullPool per task so no connection outlives the
    event loop it was opened on.
    """
    task_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(task_engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await task_engine.dispose()
