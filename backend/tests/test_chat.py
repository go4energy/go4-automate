"""Chat system tests."""

from unittest.mock import AsyncMock, patch

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}


@pytest.mark.anyio
async def test_create_conversation(client, test_tenant):
    """POST /api/v1/chat/conversations should create a conversation."""
    response = await client.post(
        "/api/v1/chat/conversations",
        json={"context_type": "general"},
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["context_type"] == "general"
    assert data["status"] == "active"
    assert data["id"] is not None


@pytest.mark.anyio
async def test_create_conversation_with_title(client, test_tenant):
    """POST /api/v1/chat/conversations should accept optional title."""
    response = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Onboarding Chat", "context_type": "onboarding"},
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Onboarding Chat"
    assert data["context_type"] == "onboarding"


@pytest.mark.anyio
async def test_list_conversations_empty(client, test_tenant):
    """GET /api/v1/chat/conversations should return empty list."""
    response = await client.get(
        "/api/v1/chat/conversations",
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_conversations(client, test_tenant):
    """GET /api/v1/chat/conversations should return created conversations."""
    # Create two conversations
    await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Conv 1", "context_type": "general"},
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Conv 2", "context_type": "research"},
        headers=HEADERS,
    )

    response = await client.get(
        "/api/v1/chat/conversations",
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_conversation(client, test_tenant):
    """GET /api/v1/chat/conversations/{id} should return conversation with messages."""
    create_resp = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Test Conv", "context_type": "general"},
        headers=HEADERS,
    )
    conv_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert data["title"] == "Test Conv"
    assert data["messages"] == []


@pytest.mark.anyio
async def test_get_conversation_not_found(client, test_tenant):
    """GET /api/v1/chat/conversations/999 should return 404."""
    response = await client.get(
        "/api/v1/chat/conversations/999",
        headers=HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_conversation(client, test_tenant):
    """DELETE /api/v1/chat/conversations/{id} should delete."""
    create_resp = await client.post(
        "/api/v1/chat/conversations",
        json={"context_type": "general"},
        headers=HEADERS,
    )
    conv_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=HEADERS,
    )
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=HEADERS,
    )
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_send_message_streams_response(client, test_tenant):
    """POST /api/v1/chat/conversations/{id}/messages should return SSE stream."""
    create_resp = await client.post(
        "/api/v1/chat/conversations",
        json={"context_type": "general"},
        headers=HEADERS,
    )
    conv_id = create_resp.json()["id"]

    mock_stream = AsyncMock()
    mock_stream.__aiter__ = lambda self: self
    chunks = iter(["Hallo", ", wie", " kann", " ich", " helfen?"])
    mock_stream.__anext__ = AsyncMock(
        side_effect=lambda: next(chunks, (_ for _ in ()).throw(StopAsyncIteration))
    )

    async def mock_stream_generate(*args, **kwargs):
        for text in ["Hallo", ", wie", " kann", " ich", " helfen?"]:
            yield text

    with patch(
        "app.services.chat.LLMService.stream_generate",
        side_effect=mock_stream_generate,
    ):
        response = await client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            json={"content": "Hallo!"},
            headers=HEADERS,
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "delta" in body
        assert "done" in body


@pytest.mark.anyio
async def test_send_message_to_nonexistent_conversation(client, test_tenant):
    """POST messages to nonexistent conversation should return 404."""
    response = await client.post(
        "/api/v1/chat/conversations/999/messages",
        json={"content": "test"},
        headers=HEADERS,
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_conversation_tenant_isolation(client, test_tenant):
    """Conversations should be isolated per tenant."""
    # Create conversation for test-tenant
    await client.post(
        "/api/v1/chat/conversations",
        json={"context_type": "general"},
        headers=HEADERS,
    )

    # Try to list with different tenant
    response = await client.get(
        "/api/v1/chat/conversations",
        headers={"X-Tenant-ID": "other-tenant"},
    )
    assert response.status_code == 200
    assert response.json() == []
