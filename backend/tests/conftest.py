"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Fix paths for tests running from backend/ directory
settings.template_dir = "../config/templates"
settings.tenant_config_dir = "../config/tenants"


# JSONB is not supported by SQLite - compile as JSON instead
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# Use SQLite for tests (no external DB needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Test DB session override."""
    async with test_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for tests."""
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Provide a test DB session."""
    async with test_session() as session:
        yield session


@pytest.fixture
async def client():
    """Async HTTP test client with DB override."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_tenant(client):
    """Create a test tenant and return its data."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "test-tenant", "tenant_name": "Test Tenant GmbH"},
    )
    assert response.status_code == 201
    return response.json()
