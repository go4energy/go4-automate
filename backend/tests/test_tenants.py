"""Tenant API tests."""

import pytest


@pytest.mark.anyio
async def test_create_tenant(client):
    """POST /api/v1/tenants should create a tenant."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "new-tenant", "tenant_name": "New Tenant GmbH"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tenant_id"] == "new-tenant"
    assert data["tenant_name"] == "New Tenant GmbH"
    assert data["active"] is True


@pytest.mark.anyio
async def test_create_duplicate_tenant(client, test_tenant):
    """POST /api/v1/tenants with existing tenant_id should return 409."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "test-tenant", "tenant_name": "Duplicate"},
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_list_tenants(client, test_tenant):
    """GET /api/v1/tenants should list all tenants."""
    response = await client.get("/api/v1/tenants")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(t["tenant_id"] == "test-tenant" for t in data)


@pytest.mark.anyio
async def test_get_tenant(client, test_tenant):
    """GET /api/v1/tenants/{id} should return a specific tenant."""
    response = await client.get("/api/v1/tenants/test-tenant")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_get_nonexistent_tenant(client):
    """GET /api/v1/tenants/{id} with unknown ID should return 404."""
    response = await client.get("/api/v1/tenants/nonexistent")
    assert response.status_code == 404
