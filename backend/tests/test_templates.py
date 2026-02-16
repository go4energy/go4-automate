"""Template API tests."""

import pytest


@pytest.mark.anyio
async def test_list_templates(client):
    """GET /api/v1/templates should list available templates."""
    response = await client.get("/api/v1/templates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_get_template(client):
    """GET /api/v1/templates/{cat}/{file} should return template content."""
    response = await client.get("/api/v1/templates/follow-up/default.html")
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "follow-up"
    assert data["filename"] == "default.html"
    assert "{{company_name}}" in data["content"]


@pytest.mark.anyio
async def test_get_nonexistent_template(client):
    """GET /api/v1/templates/{cat}/{file} with unknown file should return 404."""
    response = await client.get("/api/v1/templates/follow-up/nonexistent.html")
    assert response.status_code == 404
