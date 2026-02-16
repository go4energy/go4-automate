"""Health endpoint tests."""

import pytest


@pytest.mark.anyio
async def test_health_returns_200(client):
    """Health endpoint should return 200 with status healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
