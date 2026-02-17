"""Ad campaign API tests."""

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

CAMPAIGN_PAYLOAD = {
    "platform": "meta",
    "name": "Frühjahrskampagne 2026",
    "objective": "lead_generation",
    "daily_budget": "50.00",
    "start_date": "2026-03-01",
}


@pytest.mark.anyio
async def test_create_campaign(client, test_tenant):
    """POST /api/v1/ad-campaigns should create a campaign."""
    response = await client.post(
        "/api/v1/ad-campaigns", json=CAMPAIGN_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == CAMPAIGN_PAYLOAD["name"]
    assert data["platform"] == "meta"
    assert data["status"] == "draft"
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_list_campaigns(client, test_tenant):
    """GET /api/v1/ad-campaigns should list campaigns for tenant."""
    await client.post("/api/v1/ad-campaigns", json=CAMPAIGN_PAYLOAD, headers=HEADERS)
    second = {**CAMPAIGN_PAYLOAD, "name": "Zweite Kampagne", "platform": "google"}
    await client.post("/api/v1/ad-campaigns", json=second, headers=HEADERS)

    response = await client.get("/api/v1/ad-campaigns", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_campaign(client, test_tenant):
    """GET /api/v1/ad-campaigns/{id} should return a single campaign."""
    create_resp = await client.post(
        "/api/v1/ad-campaigns", json=CAMPAIGN_PAYLOAD, headers=HEADERS
    )
    campaign_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/ad-campaigns/{campaign_id}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == campaign_id


@pytest.mark.anyio
async def test_get_nonexistent_campaign(client, test_tenant):
    """GET /api/v1/ad-campaigns/999 should return 404."""
    response = await client.get("/api/v1/ad-campaigns/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_campaign(client, test_tenant):
    """PUT /api/v1/ad-campaigns/{id} should update a campaign."""
    create_resp = await client.post(
        "/api/v1/ad-campaigns", json=CAMPAIGN_PAYLOAD, headers=HEADERS
    )
    campaign_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/ad-campaigns/{campaign_id}",
        json={"status": "active", "daily_budget": "75.00"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_delete_campaign(client, test_tenant):
    """DELETE /api/v1/ad-campaigns/{id} should delete a campaign."""
    create_resp = await client.post(
        "/api/v1/ad-campaigns", json=CAMPAIGN_PAYLOAD, headers=HEADERS
    )
    campaign_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/ad-campaigns/{campaign_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/ad-campaigns/{campaign_id}", headers=HEADERS)
    assert get_resp.status_code == 404
