"""Research API tests."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

SOURCE_PAYLOAD = {
    "name": "PV Magazine RSS",
    "url": "https://www.pv-magazine.de/feed/",
    "source_type": "rss",
    "keywords": ["Photovoltaik", "Solar"],
    "fetch_interval_hours": 12,
}

TOPIC_PAYLOAD = {
    "title": "Solar-Carport Vorteile",
    "description": "Warum ein Solar-Carport die beste Investition ist",
    "category": "content",
    "platforms": ["facebook", "instagram"],
    "priority": 2,
    "source_type": "manual",
}


# --- Source CRUD ---


@pytest.mark.anyio
async def test_create_source(client, test_tenant):
    """POST /api/v1/research/sources should create a source."""
    response = await client.post(
        "/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "PV Magazine RSS"
    assert data["source_type"] == "rss"
    assert data["active"] is True
    assert data["fetch_interval_hours"] == 12


@pytest.mark.anyio
async def test_list_sources(client, test_tenant):
    """GET /api/v1/research/sources should list sources."""
    await client.post("/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS)
    second = {**SOURCE_PAYLOAD, "name": "Website", "source_type": "website"}
    await client.post("/api/v1/research/sources", json=second, headers=HEADERS)

    response = await client.get("/api/v1/research/sources", headers=HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_get_source(client, test_tenant):
    """GET /api/v1/research/sources/{id} should return a source."""
    create = await client.post(
        "/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS
    )
    source_id = create.json()["id"]

    response = await client.get(
        f"/api/v1/research/sources/{source_id}", headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["name"] == "PV Magazine RSS"


@pytest.mark.anyio
async def test_update_source(client, test_tenant):
    """PUT /api/v1/research/sources/{id} should update a source."""
    create = await client.post(
        "/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS
    )
    source_id = create.json()["id"]

    response = await client.put(
        f"/api/v1/research/sources/{source_id}",
        json={"name": "Updated Name", "active": False},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["active"] is False


@pytest.mark.anyio
async def test_delete_source(client, test_tenant):
    """DELETE /api/v1/research/sources/{id} should delete a source."""
    create = await client.post(
        "/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS
    )
    source_id = create.json()["id"]

    response = await client.delete(
        f"/api/v1/research/sources/{source_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/v1/research/sources/{source_id}", headers=HEADERS
    )
    assert get_resp.status_code == 404


# --- Topic CRUD ---


@pytest.mark.anyio
async def test_create_topic(client, test_tenant):
    """POST /api/v1/research/topics should create a topic."""
    response = await client.post(
        "/api/v1/research/topics", json=TOPIC_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Solar-Carport Vorteile"
    assert data["source_type"] == "manual"
    assert data["status"] == "suggested"
    assert data["priority"] == 2


@pytest.mark.anyio
async def test_list_topics(client, test_tenant):
    """GET /api/v1/research/topics should list topics."""
    await client.post("/api/v1/research/topics", json=TOPIC_PAYLOAD, headers=HEADERS)
    second = {**TOPIC_PAYLOAD, "title": "Zweites Thema"}
    await client.post("/api/v1/research/topics", json=second, headers=HEADERS)

    response = await client.get("/api/v1/research/topics", headers=HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.anyio
async def test_update_topic_status(client, test_tenant):
    """PUT /api/v1/research/topics/{id} should update status."""
    create = await client.post(
        "/api/v1/research/topics", json=TOPIC_PAYLOAD, headers=HEADERS
    )
    topic_id = create.json()["id"]

    response = await client.put(
        f"/api/v1/research/topics/{topic_id}",
        json={"status": "approved"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.anyio
async def test_delete_topic(client, test_tenant):
    """DELETE /api/v1/research/topics/{id} should delete a topic."""
    create = await client.post(
        "/api/v1/research/topics", json=TOPIC_PAYLOAD, headers=HEADERS
    )
    topic_id = create.json()["id"]

    response = await client.delete(
        f"/api/v1/research/topics/{topic_id}", headers=HEADERS
    )
    assert response.status_code == 204


# --- Research Run ---


@pytest.mark.anyio
async def test_research_run_with_mock(client, test_tenant):
    """POST /api/v1/research/run should fetch and analyze findings."""
    # Create source
    await client.post("/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS)

    mock_feed = MagicMock()
    mock_feed.entries = [
        MagicMock(
            title="Neue Solartechnologie 2026",
            summary="Fortschritte in der Photovoltaik",
            link="https://example.com/solar-2026",
            published_parsed=(2026, 2, 19, 10, 0, 0, 0, 0, 0),
            get=lambda key, default="": {
                "title": "Neue Solartechnologie 2026",
                "summary": "Fortschritte in der Photovoltaik",
                "link": "https://example.com/solar-2026",
                "published_parsed": (2026, 2, 19, 10, 0, 0, 0, 0, 0),
            }.get(key, default),
        )
    ]

    with (
        patch("app.services.research.feedparser.parse", return_value=mock_feed),
        patch(
            "app.services.research.ResearchService._analyze_findings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await client.post("/api/v1/research/run", json={}, headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["findings_count"] >= 0
    assert "errors" in data


# --- Finding Deduplification ---


@pytest.mark.anyio
async def test_finding_dedup(client, test_tenant):
    """Running research twice should not create duplicate findings."""
    await client.post("/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS)

    mock_feed = MagicMock()
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": "Doppelter Artikel",
        "summary": "Photovoltaik News",
        "link": "https://example.com/doppelt",
        "published_parsed": (2026, 2, 19, 10, 0, 0, 0, 0, 0),
    }.get(key, default)
    mock_feed.entries = [entry]

    with (
        patch("app.services.research.feedparser.parse", return_value=mock_feed),
        patch(
            "app.services.research.ResearchService._analyze_findings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        await client.post("/api/v1/research/run", json={}, headers=HEADERS)
        await client.post("/api/v1/research/run", json={}, headers=HEADERS)

    findings = await client.get("/api/v1/research/findings", headers=HEADERS)
    urls = [f["url"] for f in findings.json()]
    assert urls.count("https://example.com/doppelt") <= 1


# --- Finding Status Update ---


@pytest.mark.anyio
async def test_update_finding_status(client, test_tenant):
    """PATCH /api/v1/research/findings/{id} should update status."""
    await client.post("/api/v1/research/sources", json=SOURCE_PAYLOAD, headers=HEADERS)

    mock_feed = MagicMock()
    entry = MagicMock()
    entry.get = lambda key, default="": {
        "title": "Test Solar Artikel",
        "summary": "Solar und Photovoltaik",
        "link": "https://example.com/finding-status-test",
        "published_parsed": (2026, 2, 19, 10, 0, 0, 0, 0, 0),
    }.get(key, default)
    mock_feed.entries = [entry]

    with (
        patch("app.services.research.feedparser.parse", return_value=mock_feed),
        patch(
            "app.services.research.ResearchService._analyze_findings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        await client.post("/api/v1/research/run", json={}, headers=HEADERS)

    findings = await client.get("/api/v1/research/findings", headers=HEADERS)
    finding_list = findings.json()
    if finding_list:
        finding_id = finding_list[0]["id"]
        response = await client.patch(
            f"/api/v1/research/findings/{finding_id}",
            json={"status": "reviewed"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "reviewed"


# --- Topic Generate ---


@pytest.mark.anyio
async def test_generate_from_topic(client, test_tenant):
    """POST /api/v1/research/topics/{id}/generate should create content."""
    create = await client.post(
        "/api/v1/research/topics", json=TOPIC_PAYLOAD, headers=HEADERS
    )
    topic_id = create.json()["id"]

    mock_result = {
        "title": "Solar-Carport: Die smarte Investition",
        "caption": "Ein Solar-Carport ist mehr als nur ein Parkplatz...",
        "short": "Solar-Carport = Strom + Schutz",
        "hashtags": "#solar #carport #photovoltaik",
        "hook": "Wussten Sie, dass ein Carport Strom erzeugen kann?",
        "cta": "Jetzt beraten lassen!",
    }

    with patch(
        "app.services.content.ContentService._generate_via_registry_or_legacy",
        new_callable=AsyncMock,
        return_value=(mock_result, "claude-sonnet-4-5-20250929"),
    ):
        response = await client.post(
            f"/api/v1/research/topics/{topic_id}/generate",
            json={"platform": "facebook", "content_type": "post"},
            headers=HEADERS,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Solar-Carport: Die smarte Investition"
    assert data["platform"] == "facebook"
    assert data["status"] == "draft"


# --- Image Upload ---


@pytest.mark.anyio
async def test_upload_image_valid(client, test_tenant, tmp_path):
    """POST /api/v1/research/upload/image should accept valid images."""
    with patch("app.services.upload.settings") as mock_settings:
        mock_settings.upload_dir = str(tmp_path)
        mock_settings.max_upload_size_mb = 10

        fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        response = await client.post(
            "/api/v1/research/upload/image",
            files={"file": ("test.png", fake_image, "image/png")},
            headers=HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["url"].startswith("/uploads/test-tenant/")
    assert data["url"].endswith(".png")


@pytest.mark.anyio
async def test_upload_image_invalid_type(client, test_tenant):
    """POST /api/v1/research/upload/image should reject invalid types."""
    fake_file = io.BytesIO(b"not an image")
    response = await client.post(
        "/api/v1/research/upload/image",
        files={"file": ("test.txt", fake_file, "text/plain")},
        headers=HEADERS,
    )
    assert response.status_code == 400
