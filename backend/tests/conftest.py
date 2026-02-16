"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for tests."""
    return "asyncio"


@pytest.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_health(client):
    """Verify health endpoint works."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
