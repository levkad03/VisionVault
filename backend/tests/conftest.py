import asyncio

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app

BASE_URL = settings.database_url.rsplit("/", 1)[0]
TEST_DATABASE_URL = f"{BASE_URL}/visionvault_test"
ADMIN_DATABASE_URL = f"{BASE_URL}/postgres"


async def _create_test_database() -> None:
    dsn = ADMIN_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'visionvault_test'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE visionvault_test")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def _test_database_created():
    asyncio.run(_create_test_database())


@pytest.fixture(scope="session")
async def engine(_test_database_created):
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine):
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    async with engine.connect() as conn:
        async with conn.begin() as trans:
            async with session_factory(bind=conn) as session:
                yield session
            await trans.rollback()


@pytest.fixture
async def client(session):
    app.dependency_overrides[get_db] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
