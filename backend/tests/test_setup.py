"""Setup wizard tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}


@pytest.mark.anyio
async def test_create_setup_conversation(client, test_tenant):
    """POST /api/v1/setup/conversations should create a setup conversation."""
    response = await client.post(
        "/api/v1/setup/conversations",
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["context_type"] == "setup"
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_list_setup_conversations(client, test_tenant):
    """GET /api/v1/setup/conversations should list only setup conversations."""
    # Create setup conversation
    await client.post("/api/v1/setup/conversations", headers=HEADERS)
    # Create regular chat conversation
    await client.post(
        "/api/v1/chat/conversations",
        json={"context_type": "general"},
        headers=HEADERS,
    )

    response = await client.get("/api/v1/setup/conversations", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["context_type"] == "setup"


@pytest.mark.anyio
async def test_get_setup_conversation(client, test_tenant):
    """GET /api/v1/setup/conversations/{id} should return conversation."""
    create_resp = await client.post("/api/v1/setup/conversations", headers=HEADERS)
    conv_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/setup/conversations/{conv_id}", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["context_type"] == "setup"


@pytest.mark.anyio
async def test_delete_setup_conversation(client, test_tenant):
    """DELETE /api/v1/setup/conversations/{id} should delete."""
    create_resp = await client.post("/api/v1/setup/conversations", headers=HEADERS)
    conv_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/setup/conversations/{conv_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/v1/setup/conversations/{conv_id}", headers=HEADERS
    )
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_get_setup_status(client, test_tenant):
    """GET /api/v1/setup/status should return module progress."""
    response = await client.get("/api/v1/setup/status", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "modules" in data
    assert "tenant" in data["modules"]
    assert "collector" in data["modules"]
    assert "creator" in data["modules"]
    assert "campaigns" in data["modules"]
    assert "integrations" in data["modules"]
    for mod in data["modules"].values():
        assert "label" in mod
        assert "configured" in mod
        assert "details" in mod


@pytest.mark.anyio
async def test_send_setup_message_streams(client, test_tenant):
    """POST /api/v1/setup/conversations/{id}/messages should return SSE stream."""
    create_resp = await client.post("/api/v1/setup/conversations", headers=HEADERS)
    conv_id = create_resp.json()["id"]

    # Mock the Anthropic API response
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Willkommen beim Setup!"

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with (
        patch("anthropic.AsyncAnthropic", return_value=mock_client),
        patch("app.setup.service.settings") as mock_settings,
    ):
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.llm_model_content = "claude-sonnet-4-5-20250929"
        mock_settings.tenant_config_dir = "../config/tenants"
        response = await client.post(
            f"/api/v1/setup/conversations/{conv_id}/messages",
            json={"content": "Hallo!"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "delta" in body
        assert "done" in body


@pytest.mark.anyio
async def test_send_message_to_nonexistent_setup_conversation(client, test_tenant):
    """POST messages to nonexistent setup conversation should return 404."""
    response = await client.post(
        "/api/v1/setup/conversations/999/messages",
        json={"content": "test"},
        headers=HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_setup_skills_loading():
    """Skills files should be loadable."""
    from app.setup.service import SetupAgentService

    service = SetupAgentService.__new__(SetupAgentService)
    service._skills_cache = None
    skills = service._load_skills()
    assert "_overview" in skills
    assert "tenant" in skills
    assert "tenant" in skills
    assert "integrations" in skills
    assert "integrations" in skills
