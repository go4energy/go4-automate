"""Content API tests."""

from unittest.mock import AsyncMock, patch

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


# === Content Pipeline Tests ===


@pytest.mark.anyio
async def test_generate_content(client, test_tenant):
    """POST /api/v1/content/pieces/generate should create an AI-generated draft."""
    mock_json = {
        "title": "KI-generierter Titel",
        "caption": "Toller Post über Energie",
        "short": "Kurz und knapp",
        "hashtags": "#energie #solar",
        "hook": "Wussten Sie schon?",
        "cta": "Jetzt mehr erfahren!",
    }

    with patch(
        "app.services.content.LLMService.generate_json",
        new_callable=AsyncMock,
        return_value=mock_json,
    ):
        response = await client.post(
            "/api/v1/content/pieces/generate",
            json={
                "topic": "Energieeffizienz",
                "platform": "facebook",
                "content_type": "post",
            },
            headers=HEADERS,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["title"] == "KI-generierter Titel"
    assert data["caption"] == "Toller Post über Energie"
    assert data["created_by"] == "ai"
    assert data["ai_model"] is not None


@pytest.mark.anyio
async def test_approve_content(client, test_tenant):
    """PATCH /api/v1/content/pieces/{id}/approve should set scheduled status."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/content/pieces/{piece_id}/approve",
        json={
            "approved_by": "tester",
            "scheduled_at": "2026-03-15T10:00:00",
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["approved_by"] == "tester"
    assert data["approved_at"] is not None
    assert data["scheduled_at"] is not None


@pytest.mark.anyio
async def test_approve_published_fails(client, test_tenant):
    """PATCH approve on a published piece should fail with 400."""
    create_resp = await client.post(
        "/api/v1/content/pieces",
        json={**PIECE_PAYLOAD, "status": "published"},
        headers=HEADERS,
    )
    piece_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/content/pieces/{piece_id}/approve",
        json={
            "approved_by": "tester",
            "scheduled_at": "2026-03-15T10:00:00",
        },
        headers=HEADERS,
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_publish_requires_scheduled(client, test_tenant):
    """POST publish on a draft piece should fail with 400."""
    create_resp = await client.post(
        "/api/v1/content/pieces", json=PIECE_PAYLOAD, headers=HEADERS
    )
    piece_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/content/pieces/{piece_id}/publish",
        headers=HEADERS,
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_theme_rotation(client, test_tenant):
    """POST /api/v1/content/themes/rotation should return first topic when no history."""
    topics = ["Energie", "Solar", "Wärme"]
    response = await client.post(
        "/api/v1/content/themes/rotation",
        json=topics,
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["next_topic"] == "Energie"
    assert data["topics"] == topics


@pytest.mark.anyio
async def test_theme_rotation_after_usage(client, test_tenant):
    """Theme rotation should return the next topic after one was used."""
    topics = ["Energie", "Solar", "Wärme"]

    # Create a piece with topic "Energie"
    await client.post(
        "/api/v1/content/pieces",
        json={**PIECE_PAYLOAD, "topic": "Energie"},
        headers=HEADERS,
    )

    response = await client.post(
        "/api/v1/content/themes/rotation",
        json=topics,
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["next_topic"] == "Solar"
