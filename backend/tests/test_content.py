"""Content API tests."""

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

PIECE_PAYLOAD = {
    "title": "5 Tipps für Energieeffizienz",
    "content_type": "post",
    "platform": "linkedin",
    "caption": "Energieeffizienz leicht gemacht!",
    "hashtags": "#energie #effizienz",
    "funnel_stage": "awareness",
}


@pytest.mark.anyio
async def test_create_content_piece(client, test_tenant):
    """POST /api/v1/content/pieces should create a content piece."""
    response = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == PIECE_PAYLOAD["title"]
    assert data["platform"] == "linkedin"
    assert data["status"] == "draft"
    assert data["reach"] == 0
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_list_content_pieces(client, test_tenant):
    """GET /api/v1/content/pieces should list pieces for tenant."""
    await client.post("/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS)
    second = {**PIECE_PAYLOAD, "title": "Zweiter Post", "platform": "instagram"}
    await client.post("/api/v1/content/pieces", json=second, headers=HEADERS)

    response = await client.get("/api/v1/content/pieces", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_list_content_pieces_filter_status(client, test_tenant):
    """GET /api/v1/content/pieces?status=draft should filter by status."""
    await client.post("/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS)

    response = await client.get("/api/v1/content/pieces?status=draft", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert all(p["status"] == "draft" for p in data)


@pytest.mark.anyio
async def test_list_content_pieces_filter_platform(client, test_tenant):
    """GET /api/v1/content/pieces?platform=linkedin should filter by platform."""
    await client.post("/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS)
    other = {**PIECE_PAYLOAD, "title": "Insta Post", "platform": "instagram"}
    await client.post("/api/v1/content/pieces", json=other, headers=HEADERS)

    response = await client.get(
        "/api/v1/content/pieces?platform=linkedin", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["platform"] == "linkedin"


@pytest.mark.anyio
async def test_get_content_piece(client, test_tenant):
    """GET /api/v1/content/pieces/{id} should return a single piece."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/content/pieces/{piece_id}", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["id"] == piece_id


@pytest.mark.anyio
async def test_get_nonexistent_piece(client, test_tenant):
    """GET /api/v1/content/pieces/999 should return 404."""
    response = await client.get("/api/v1/content/pieces/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_content_piece(client, test_tenant):
    """PUT /api/v1/content/pieces/{id} should update a piece."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/content/pieces/{piece_id}",
        json={"status": "scheduled", "caption": "Neuer Text"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["caption"] == "Neuer Text"


@pytest.mark.anyio
async def test_delete_content_piece(client, test_tenant):
    """DELETE /api/v1/content/pieces/{id} should delete a piece."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/content/pieces/{piece_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/content/pieces/{piece_id}", headers=HEADERS)
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_create_calendar_entry(client, test_tenant):
    """POST /api/v1/content/calendar should create a calendar entry."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    cal_payload = {
        "content_id": piece_id,
        "platform": "linkedin",
        "scheduled_at": "2026-03-01T10:00:00",
        "time_slot": "morning",
    }
    response = await client.post(
        "/api/v1/content/calendar", json=cal_payload, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content_id"] == piece_id
    assert data["is_posted"] is False


@pytest.mark.anyio
async def test_list_calendar(client, test_tenant):
    """GET /api/v1/content/calendar should list calendar entries."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    cal_payload = {
        "content_id": piece_id,
        "platform": "linkedin",
        "scheduled_at": "2026-03-01T10:00:00",
    }
    await client.post("/api/v1/content/calendar", json=cal_payload, headers=HEADERS)

    response = await client.get("/api/v1/content/calendar", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
