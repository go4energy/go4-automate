"""Lead API tests."""

import pytest


@pytest.mark.anyio
async def test_create_lead(client, test_tenant):
    """POST /api/v1/leads should create a lead."""
    response = await client.post(
        "/api/v1/leads",
        json={
            "email": "test@example.com",
            "name": "Max Mustermann",
            "phone": "+43 1 234 5678",
            "source": "website",
        },
        headers={"X-Tenant-ID": "test-tenant"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Max Mustermann"
    assert data["status"] == "new"
    assert data["score"] == 0
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_create_duplicate_lead(client, test_tenant):
    """POST /api/v1/leads with duplicate email should return 409."""
    payload = {
        "email": "dup@example.com",
        "name": "Erster Lead",
    }
    headers = {"X-Tenant-ID": "test-tenant"}
    response1 = await client.post("/api/v1/leads", json=payload, headers=headers)
    assert response1.status_code == 201

    response2 = await client.post("/api/v1/leads", json=payload, headers=headers)
    assert response2.status_code == 409


@pytest.mark.anyio
async def test_list_leads(client, test_tenant):
    """GET /api/v1/leads should list leads for tenant."""
    headers = {"X-Tenant-ID": "test-tenant"}
    await client.post(
        "/api/v1/leads",
        json={"email": "a@example.com", "name": "A"},
        headers=headers,
    )
    await client.post(
        "/api/v1/leads",
        json={"email": "b@example.com", "name": "B"},
        headers=headers,
    )

    response = await client.get("/api/v1/leads", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_list_leads_filter_status(client, test_tenant):
    """GET /api/v1/leads?status=new should filter by status."""
    headers = {"X-Tenant-ID": "test-tenant"}
    await client.post(
        "/api/v1/leads",
        json={"email": "c@example.com", "name": "C"},
        headers=headers,
    )

    response = await client.get("/api/v1/leads?status=new", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert all(lead["status"] == "new" for lead in data)


@pytest.mark.anyio
async def test_update_lead_status(client, test_tenant):
    """PATCH /api/v1/leads/{id}/status should update status."""
    headers = {"X-Tenant-ID": "test-tenant"}
    create_resp = await client.post(
        "/api/v1/leads",
        json={"email": "d@example.com", "name": "D"},
        headers=headers,
    )
    lead_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "contacted"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "contacted"


@pytest.mark.anyio
async def test_pause_followup(client, test_tenant):
    """PATCH /api/v1/leads/{id}/pause-followup should toggle pause."""
    headers = {"X-Tenant-ID": "test-tenant"}
    create_resp = await client.post(
        "/api/v1/leads",
        json={"email": "e@example.com", "name": "E"},
        headers=headers,
    )
    lead_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/leads/{lead_id}/pause-followup",
        json={"paused": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["followup_paused"] is True
