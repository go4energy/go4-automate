"""Prompt registry API tests."""

from unittest.mock import AsyncMock, patch

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

PROMPT_PAYLOAD = {
    "slug": "test-prompt",
    "name": "Test Prompt",
    "description": "Ein Test-Prompt",
    "category": "content",
    "system_prompt": "Du bist ein Assistent für {{COMPANY_NAME}}.",
    "user_prompt": "Erstelle einen Post über {{topic}}.",
    "variables": [
        {
            "name": "topic",
            "type": "string",
            "required": True,
            "default": None,
            "description": "Das Thema",
        },
        {
            "name": "COMPANY_NAME",
            "type": "string",
            "required": False,
            "default": "TestFirma",
            "description": "Firmenname",
        },
    ],
    "output_format": "text",
    "provider": "anthropic",
    "model": "claude-sonnet-4-5-20250929",
    "temperature": 0.7,
    "max_tokens": 2048,
}


@pytest.mark.anyio
async def test_create_prompt(client, test_tenant):
    """POST /api/v1/prompts/ should create a prompt."""
    response = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-prompt"
    assert data["name"] == "Test Prompt"
    assert data["version"] == 1
    assert data["is_active"] is True
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_list_prompts(client, test_tenant):
    """GET /api/v1/prompts/ should list prompts."""
    await client.post("/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS)
    second = {**PROMPT_PAYLOAD, "slug": "second-prompt", "name": "Zweiter Prompt"}
    await client.post("/api/v1/prompts/", json=second, headers=HEADERS)

    response = await client.get("/api/v1/prompts/", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_list_prompts_filter_category(client, test_tenant):
    """GET /api/v1/prompts/?category=content should filter by category."""
    await client.post("/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS)
    other = {**PROMPT_PAYLOAD, "slug": "analysis-prompt", "category": "analysis"}
    await client.post("/api/v1/prompts/", json=other, headers=HEADERS)

    response = await client.get("/api/v1/prompts/?category=content", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "content"


@pytest.mark.anyio
async def test_get_prompt(client, test_tenant):
    """GET /api/v1/prompts/{id} should return a single prompt."""
    create_resp = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    prompt_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/prompts/{prompt_id}", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prompt_id
    assert data["system_prompt"] == PROMPT_PAYLOAD["system_prompt"]


@pytest.mark.anyio
async def test_get_nonexistent_prompt(client, test_tenant):
    """GET /api/v1/prompts/999 should return 404."""
    response = await client.get("/api/v1/prompts/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_prompt(client, test_tenant):
    """PUT /api/v1/prompts/{id} should update a prompt."""
    create_resp = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    prompt_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/prompts/{prompt_id}",
        json={"name": "Updated Name", "temperature": 0.9},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["temperature"] == 0.9


@pytest.mark.anyio
async def test_delete_prompt(client, test_tenant):
    """DELETE /api/v1/prompts/{id} should delete a prompt."""
    create_resp = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    prompt_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/prompts/{prompt_id}", headers=HEADERS)
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/prompts/{prompt_id}", headers=HEADERS)
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_duplicate_slug_returns_409(client, test_tenant):
    """POST /api/v1/prompts/ with duplicate slug should return 409."""
    await client.post("/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS)
    response = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_create_version(client, test_tenant):
    """POST /api/v1/prompts/{id}/version should create v2 and deactivate v1."""
    create_resp = await client.post(
        "/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS
    )
    prompt_id = create_resp.json()["id"]

    version_resp = await client.post(
        f"/api/v1/prompts/{prompt_id}/version", headers=HEADERS
    )
    assert version_resp.status_code == 201
    v2 = version_resp.json()
    assert v2["version"] == 2
    assert v2["is_active"] is True

    # Check that v1 is now inactive
    v1_resp = await client.get(f"/api/v1/prompts/{prompt_id}", headers=HEADERS)
    assert v1_resp.json()["is_active"] is False


@pytest.mark.anyio
async def test_execute_prompt(client, test_tenant):
    """POST /api/v1/llm/execute should execute a prompt from registry."""
    await client.post("/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS)

    with patch(
        "app.services.llm.LLMService.generate_with_config",
        new_callable=AsyncMock,
        return_value="Hier ist der generierte Text.",
    ):
        response = await client.post(
            "/api/v1/llm/execute",
            json={
                "prompt_slug": "test-prompt",
                "variables": {"topic": "Photovoltaik"},
            },
            headers=HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["prompt_slug"] == "test-prompt"
    assert data["result"] == "Hier ist der generierte Text."
    assert data["version"] == 1


@pytest.mark.anyio
async def test_execute_missing_required_variable(client, test_tenant):
    """POST /api/v1/llm/execute with missing required variable should return 400."""
    await client.post("/api/v1/prompts/", json=PROMPT_PAYLOAD, headers=HEADERS)

    response = await client.post(
        "/api/v1/llm/execute",
        json={
            "prompt_slug": "test-prompt",
            "variables": {},
        },
        headers=HEADERS,
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_execute_nonexistent_slug(client, test_tenant):
    """POST /api/v1/llm/execute with unknown slug should return 404."""
    response = await client.post(
        "/api/v1/llm/execute",
        json={
            "prompt_slug": "nonexistent",
            "variables": {},
        },
        headers=HEADERS,
    )
    assert response.status_code == 404
