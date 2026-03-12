"""Shared test fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

# Fix paths for tests running from backend/ directory
settings.template_dir = "../config/templates"
settings.tenant_config_dir = "../config/tenants"

# Set backend_secret for test auth bypass
settings.backend_secret = "test-secret"
TEST_AUTH_HEADERS = {"X-Backend-Secret": "test-secret"}


# JSONB is not supported by SQLite - compile as JSON instead
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


# Use synchronous SQLite behind an async-compatible shim.
# aiosqlite hangs in this environment, while plain sqlite3 is stable.
TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = __import__("sqlalchemy").create_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
test_session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)

# With the synchronous SQLite shim, the full schema is manageable again.
TEST_TABLES = list(Base.metadata.sorted_tables)


class AsyncSessionShim:
    """Minimal async wrapper around a sync SQLAlchemy session for tests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def flush(self) -> None:
        self._session.flush()

    async def refresh(self, instance) -> None:
        self._session.refresh(instance)

    async def commit(self) -> None:
        self._session.commit()

    async def rollback(self) -> None:
        self._session.rollback()

    async def delete(self, instance) -> None:
        self._session.delete(instance)

    def add(self, instance) -> None:
        self._session.add(instance)

    def add_all(self, instances) -> None:
        self._session.add_all(instances)

    def expunge_all(self) -> None:
        self._session.expunge_all()

    def close(self) -> None:
        self._session.close()

    def __getattr__(self, name):
        return getattr(self._session, name)


async def override_get_db():
    """Test DB session override."""
    session = AsyncSessionShim(test_session_factory())
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for tests."""
    return "asyncio"


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_database():
    """Create the core test schema once for the test session."""
    Base.metadata.create_all(test_engine, tables=TEST_TABLES, checkfirst=True)
    yield
    Base.metadata.drop_all(
        test_engine, tables=list(reversed(TEST_TABLES)), checkfirst=True
    )


@pytest_asyncio.fixture(autouse=True)
async def cleanup_database():
    """Clear core test tables between tests without recreating the schema."""
    with test_engine.begin() as conn:
        for table in reversed(TEST_TABLES):
            conn.execute(delete(table))
    yield


@pytest_asyncio.fixture
async def db_session():
    """Provide a test DB session."""
    session = AsyncSessionShim(test_session_factory())
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client with DB override and auth bypass."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
        headers=TEST_AUTH_HEADERS,
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_tenant(client):
    """Create a test tenant and return its data."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "test-tenant", "tenant_name": "Test Tenant GmbH"},
    )
    assert response.status_code == 201
    return response.json()
