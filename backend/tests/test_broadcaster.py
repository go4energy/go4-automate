"""Broadcaster admin API tests."""

from unittest.mock import patch

import pytest

HEADERS = {"X-Tenant-ID": "test-tenant"}

CHANNEL_PAYLOAD = {
    "name": "Energie-Briefing",
    "slug": "energie-briefing",
    "description": "Taegliches Energie-Briefing fuer das Team",
    "target_audience": "Techniker",
    "categories": ["energie", "solar"],
    "schedule": "daily",
    "voice": "de_DE-thorsten-high",
    "language": "de",
    "max_items": 10,
    "max_duration_minutes": 5,
}

USER_PAYLOAD = {
    "email": "listener@example.com",
    "password": "secret123",
    "display_name": "Test Listener",
    "role": "techniker",
}


# --- Channel CRUD ---


@pytest.mark.anyio
async def test_create_channel(client, test_tenant):
    """POST /api/v1/broadcaster/channels should create a briefing channel."""
    response = await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == CHANNEL_PAYLOAD["name"]
    assert data["slug"] == CHANNEL_PAYLOAD["slug"]
    assert data["tenant_id"] == "test-tenant"
    assert data["active"] is True
    assert data["language"] == "de"


@pytest.mark.anyio
async def test_list_channels_empty(client, test_tenant):
    """GET /api/v1/broadcaster/channels should return empty list when no channels."""
    response = await client.get("/api/v1/broadcaster/channels", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_channels(client, test_tenant):
    """GET /api/v1/broadcaster/channels should list all channels for tenant."""
    await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    second = {**CHANNEL_PAYLOAD, "name": "Solar-Briefing", "slug": "solar-briefing"}
    await client.post("/api/v1/broadcaster/channels", json=second, headers=HEADERS)

    response = await client.get("/api/v1/broadcaster/channels", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_channel(client, test_tenant):
    """GET /api/v1/broadcaster/channels/{id} should return a single channel."""
    create_resp = await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/broadcaster/channels/{channel_id}", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == channel_id
    assert data["name"] == CHANNEL_PAYLOAD["name"]
    assert data["episode_count"] == 0
    assert data["subscriber_count"] == 0


@pytest.mark.anyio
async def test_get_channel_not_found(client, test_tenant):
    """GET /api/v1/broadcaster/channels/999 should return 404."""
    response = await client.get("/api/v1/broadcaster/channels/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_channel(client, test_tenant):
    """PUT /api/v1/broadcaster/channels/{id} should update the channel."""
    create_resp = await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/broadcaster/channels/{channel_id}",
        json={"name": "Neuer Name", "max_items": 20},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Neuer Name"
    assert data["max_items"] == 20


@pytest.mark.anyio
async def test_delete_channel(client, test_tenant):
    """DELETE /api/v1/broadcaster/channels/{id} should delete the channel."""
    create_resp = await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/broadcaster/channels/{channel_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/v1/broadcaster/channels/{channel_id}", headers=HEADERS
    )
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_channel_not_found(client, test_tenant):
    """DELETE /api/v1/broadcaster/channels/999 should return 404."""
    response = await client.delete("/api/v1/broadcaster/channels/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_channel_tenant_isolation(client, test_tenant):
    """Channels should be isolated per tenant."""
    await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )

    response = await client.get(
        "/api/v1/broadcaster/channels",
        headers={"X-Tenant-ID": "other-tenant"},
    )
    assert response.status_code == 200
    assert response.json() == []


# --- Episodes ---


@pytest.mark.anyio
async def test_list_episodes_empty(client, test_tenant):
    """GET /api/v1/broadcaster/channels/{id}/episodes should return empty list."""
    create_resp = await client.post(
        "/api/v1/broadcaster/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/broadcaster/channels/{channel_id}/episodes")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_episode_not_found(client, test_tenant):
    """GET /api/v1/broadcaster/episodes/999 should return 404."""
    response = await client.get("/api/v1/broadcaster/episodes/999")
    assert response.status_code == 404


# --- Listener User Management (Admin) ---


@pytest.mark.anyio
async def test_create_user(client, test_tenant):
    """POST /api/v1/broadcaster/users should create a listener user."""
    response = await client.post(
        "/api/v1/broadcaster/users", json=USER_PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == USER_PAYLOAD["email"]
    assert data["display_name"] == USER_PAYLOAD["display_name"]
    assert data["role"] == USER_PAYLOAD["role"]
    assert data["active"] is True
    assert data["tenant_id"] == "test-tenant"


@pytest.mark.anyio
async def test_list_users_empty(client, test_tenant):
    """GET /api/v1/broadcaster/users should return empty list when no users."""
    response = await client.get("/api/v1/broadcaster/users", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_users(client, test_tenant):
    """GET /api/v1/broadcaster/users should list all listener users for tenant."""
    await client.post("/api/v1/broadcaster/users", json=USER_PAYLOAD, headers=HEADERS)
    second = {**USER_PAYLOAD, "email": "second@example.com"}
    await client.post("/api/v1/broadcaster/users", json=second, headers=HEADERS)

    response = await client.get("/api/v1/broadcaster/users", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_delete_user(client, test_tenant):
    """DELETE /api/v1/broadcaster/users/{id} should delete the listener user."""
    create_resp = await client.post(
        "/api/v1/broadcaster/users", json=USER_PAYLOAD, headers=HEADERS
    )
    user_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/broadcaster/users/{user_id}", headers=HEADERS
    )
    assert response.status_code == 204

    # Verify user is gone
    list_resp = await client.get("/api/v1/broadcaster/users", headers=HEADERS)
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_delete_user_not_found(client, test_tenant):
    """DELETE /api/v1/broadcaster/users/999 should return 404."""
    response = await client.delete("/api/v1/broadcaster/users/999", headers=HEADERS)
    assert response.status_code == 404


# --- Config / Status / Metrics (Module Interface) ---


@pytest.mark.anyio
async def test_get_config_schema(client, test_tenant):
    """GET /api/v1/broadcaster/config/schema should return parameter definitions."""
    response = await client.get("/api/v1/broadcaster/config/schema")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    keys = [p["key"] for p in data]
    assert "llm_provider" in keys
    assert "tts_engine" in keys
    assert "self_registration" in keys


@pytest.mark.anyio
async def test_get_config(client, test_tenant):
    """GET /api/v1/broadcaster/config should return current config."""
    response = await client.get("/api/v1/broadcaster/config", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "broadcaster"
    assert "config" in data
    assert "llm_provider" in data["config"]


@pytest.mark.anyio
async def test_update_config(client, test_tenant):
    """PUT /api/v1/broadcaster/config should update module config."""
    response = await client.put(
        "/api/v1/broadcaster/config",
        json={"tts_engine": "disabled"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["tts_engine"] == "disabled"


@pytest.mark.anyio
async def test_get_status(client, test_tenant):
    """GET /api/v1/broadcaster/status should return module status."""
    with patch("app.broadcaster.tts.TTSService") as mock_tts:
        mock_tts.return_value.is_available.return_value = False
        response = await client.get("/api/v1/broadcaster/status", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "broadcaster"
    assert "healthy" in data
    assert "components" in data
    assert "channels_active" in data
    assert "listener_users" in data


@pytest.mark.anyio
async def test_get_metrics(client, test_tenant):
    """GET /api/v1/broadcaster/metrics should return KPIs."""
    response = await client.get("/api/v1/broadcaster/metrics", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "broadcaster"
    assert "metrics" in data
    metrics = data["metrics"]
    assert "episodes_total" in metrics
    assert "episodes_ready" in metrics
    assert "channels_active" in metrics
    assert "listener_users" in metrics
    assert "feedback_count" in metrics


@pytest.mark.anyio
async def test_get_metrics_with_days(client, test_tenant):
    """GET /api/v1/broadcaster/metrics?days=30 should accept days parameter."""
    response = await client.get("/api/v1/broadcaster/metrics?days=30", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "30d"
