"""Briefing admin API tests."""

from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.config import settings
from app.services.tenant import TenantService

HEADERS = {"X-Tenant-ID": "test-tenant"}

CHANNEL_PAYLOAD = {
    "name": "Energie-Briefing",
    "slug": "energie-briefing",
    "description": "Taegliches Energie-Briefing fuer das Team",
    "target_audience": "Techniker",
    "tags": ["energie", "solar"],
    "schedule": "daily",
    "voice": "de_DE-thorsten-high",
    "language": "de",
    "max_items": 10,
    "max_duration_minutes": 5,
}

SOURCE_PAYLOAD = {
    "name": "Heise RSS",
    "source_type": "rss",
    "url": "https://www.heise.de/rss/heise.rdf",
    "keywords": ["solar"],
    "fetch_interval_hours": 24,
}

USER_PAYLOAD = {
    "email": "listener@example.com",
    "password": "secret123",
    "display_name": "Test Listener",
    "role": "techniker",
}


async def _create_auth_user(client, email="user@test.de", role="user"):
    """Create an auth user and return JWT token + user_id."""
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": email,
            "password": "testpass123",
            "display_name": f"Test {role.title()}",
            "role": role,
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["id"]

    # Login to get JWT
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
        headers=HEADERS,
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return token, user_id


def _user_headers(token):
    """Build request headers for a JWT-authenticated user."""
    return {**HEADERS, "Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def personal_user(db_session, test_tenant):
    """Create a lightweight platform user and bypass auth for personal briefing tests."""
    from app.auth.dependencies import get_current_user
    from app.auth.models import User
    from app.main import app

    user = User(
        tenant_id="test-tenant",
        email="personal-briefing@test.de",
        password_hash="test-hash",
        display_name="Personal Briefing User",
        role="admin",
        active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    await db_session.commit()
    db_session.expunge_all()

    async def _override_current_user():
        return user

    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# --- Channel CRUD ---


@pytest.mark.anyio
async def test_create_channel(client, test_tenant):
    """POST /api/v1/briefing/channels should create a briefing channel."""
    response = await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
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
    """GET /api/v1/briefing/channels should return empty list when no channels."""
    response = await client.get("/api/v1/briefing/channels", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_channels(client, test_tenant):
    """GET /api/v1/briefing/channels should list all channels for tenant."""
    await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    second = {**CHANNEL_PAYLOAD, "name": "Solar-Briefing", "slug": "solar-briefing"}
    await client.post("/api/v1/briefing/channels", json=second, headers=HEADERS)

    response = await client.get("/api/v1/briefing/channels", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_channel(client, test_tenant):
    """GET /api/v1/briefing/channels/{id} should return a single channel."""
    create_resp = await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/briefing/channels/{channel_id}", headers=HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == channel_id
    assert data["name"] == CHANNEL_PAYLOAD["name"]
    assert data["episode_count"] == 0
    assert data["subscriber_count"] == 0


@pytest.mark.anyio
async def test_get_channel_not_found(client, test_tenant):
    """GET /api/v1/briefing/channels/999 should return 404."""
    response = await client.get("/api/v1/briefing/channels/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_channel(client, test_tenant):
    """PUT /api/v1/briefing/channels/{id} should update the channel."""
    create_resp = await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/briefing/channels/{channel_id}",
        json={"name": "Neuer Name", "max_items": 20},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Neuer Name"
    assert data["max_items"] == 20


@pytest.mark.anyio
async def test_delete_channel(client, test_tenant):
    """DELETE /api/v1/briefing/channels/{id} should delete the channel."""
    create_resp = await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/briefing/channels/{channel_id}", headers=HEADERS
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/v1/briefing/channels/{channel_id}", headers=HEADERS
    )
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_delete_channel_not_found(client, test_tenant):
    """DELETE /api/v1/briefing/channels/999 should return 404."""
    response = await client.delete("/api/v1/briefing/channels/999", headers=HEADERS)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_channel_tenant_isolation(client, test_tenant):
    """Channels should be isolated per tenant."""
    await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )

    response = await client.get(
        "/api/v1/briefing/channels",
        headers={"X-Tenant-ID": "other-tenant"},
    )
    assert response.status_code == 200
    assert response.json() == []


# --- Episodes ---


@pytest.mark.anyio
async def test_list_episodes_empty(client, test_tenant):
    """GET /api/v1/briefing/channels/{id}/episodes should return empty list."""
    create_resp = await client.post(
        "/api/v1/briefing/channels", json=CHANNEL_PAYLOAD, headers=HEADERS
    )
    channel_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/briefing/channels/{channel_id}/episodes")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_get_episode_not_found(client, test_tenant):
    """GET /api/v1/briefing/episodes/999 should return 404."""
    response = await client.get("/api/v1/briefing/episodes/999")
    assert response.status_code == 404


# --- Listener User Management (Admin) ---


@pytest.mark.anyio
async def test_create_user(client, test_tenant):
    """POST /api/v1/briefing/users should create a listener user."""
    response = await client.post(
        "/api/v1/briefing/users", json=USER_PAYLOAD, headers=HEADERS
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
    """GET /api/v1/briefing/users should return empty list when no users."""
    response = await client.get("/api/v1/briefing/users", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_list_users(client, test_tenant):
    """GET /api/v1/briefing/users should list all listener users for tenant."""
    await client.post("/api/v1/briefing/users", json=USER_PAYLOAD, headers=HEADERS)
    second = {**USER_PAYLOAD, "email": "second@example.com"}
    await client.post("/api/v1/briefing/users", json=second, headers=HEADERS)

    response = await client.get("/api/v1/briefing/users", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_delete_user(client, test_tenant):
    """DELETE /api/v1/briefing/users/{id} should delete the listener user."""
    create_resp = await client.post(
        "/api/v1/briefing/users", json=USER_PAYLOAD, headers=HEADERS
    )
    user_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/briefing/users/{user_id}", headers=HEADERS)
    assert response.status_code == 204

    # Verify user is gone
    list_resp = await client.get("/api/v1/briefing/users", headers=HEADERS)
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_delete_user_not_found(client, test_tenant):
    """DELETE /api/v1/briefing/users/999 should return 404."""
    response = await client.delete("/api/v1/briefing/users/999", headers=HEADERS)
    assert response.status_code == 404


# --- Config / Status / Metrics (Module Interface) ---


@pytest.mark.anyio
async def test_get_config_schema(client, test_tenant):
    """GET /api/v1/briefing/config/schema should return parameter definitions."""
    response = await client.get("/api/v1/briefing/config/schema")
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
    """GET /api/v1/briefing/config should return current config."""
    response = await client.get("/api/v1/briefing/config", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "briefing"
    assert "config" in data
    assert "llm_provider" in data["config"]


@pytest.mark.anyio
async def test_update_config(client, test_tenant):
    """PUT /api/v1/briefing/config should update module config."""
    response = await client.put(
        "/api/v1/briefing/config",
        json={"tts_engine": "disabled"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["tts_engine"] == "disabled"


@pytest.mark.anyio
async def test_get_status(client, test_tenant):
    """GET /api/v1/briefing/status should return module status."""
    with patch("app.briefing.tts.TTSService") as mock_tts:
        mock_tts.return_value.is_available.return_value = False
        response = await client.get("/api/v1/briefing/status", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "briefing"
    assert "healthy" in data
    assert "components" in data
    assert "channels_active" in data
    assert "listener_users" in data


@pytest.mark.anyio
async def test_get_metrics(client, test_tenant):
    """GET /api/v1/briefing/metrics should return KPIs."""
    response = await client.get("/api/v1/briefing/metrics", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "briefing"
    assert "metrics" in data
    metrics = data["metrics"]
    assert "episodes_total" in metrics
    assert "episodes_ready" in metrics
    assert "channels_active" in metrics
    assert "listener_users" in metrics
    assert "feedback_count" in metrics


@pytest.mark.anyio
async def test_get_metrics_with_days(client, test_tenant):
    """GET /api/v1/briefing/metrics?days=30 should accept days parameter."""
    response = await client.get("/api/v1/briefing/metrics?days=30", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "30d"


# --- Per-User Scoping: Org-wide vs Personal ---


@pytest.mark.anyio
async def test_create_org_channel_as_admin(client, test_tenant):
    """Admin can create org-wide channel with org_wide=true."""
    response = await client.post(
        "/api/v1/briefing/channels?org_wide=true",
        json=CHANNEL_PAYLOAD,
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] is None  # org-wide


@pytest.mark.anyio
async def test_create_personal_channel(client, test_tenant):
    """Channel created without org_wide belongs to the user."""
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.post(
        "/api/v1/briefing/channels",
        json={**CHANNEL_PAYLOAD, "slug": "personal-briefing"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id


@pytest.mark.anyio
async def test_user_sees_org_and_own_channels(client, test_tenant):
    """User should see org-wide channels plus their own personal channels."""
    # Admin creates org-wide channel
    await client.post(
        "/api/v1/briefing/channels?org_wide=true",
        json=CHANNEL_PAYLOAD,
        headers=HEADERS,
    )

    # Create a regular user
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    # User creates personal channel
    await client.post(
        "/api/v1/briefing/channels",
        json={**CHANNEL_PAYLOAD, "slug": "my-briefing", "name": "Mein Briefing"},
        headers=headers,
    )

    # User should see both
    response = await client.get("/api/v1/briefing/channels", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    user_ids = [ch["user_id"] for ch in data]
    assert None in user_ids  # org-wide
    assert user_id in user_ids  # personal


@pytest.mark.anyio
async def test_user_cannot_modify_org_channel(client, test_tenant):
    """Non-admin user cannot update an org-wide channel."""
    # Admin creates org-wide channel
    resp = await client.post(
        "/api/v1/briefing/channels?org_wide=true",
        json=CHANNEL_PAYLOAD,
        headers=HEADERS,
    )
    channel_id = resp.json()["id"]

    # Regular user tries to update
    token, _ = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.put(
        f"/api/v1/briefing/channels/{channel_id}",
        json={"name": "Hacked"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_user_cannot_delete_org_channel(client, test_tenant):
    """Non-admin user cannot delete an org-wide channel."""
    resp = await client.post(
        "/api/v1/briefing/channels?org_wide=true",
        json=CHANNEL_PAYLOAD,
        headers=HEADERS,
    )
    channel_id = resp.json()["id"]

    token, _ = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.delete(
        f"/api/v1/briefing/channels/{channel_id}", headers=headers
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_clone_org_channel(client, test_tenant):
    """User can clone an org-wide channel as a personal channel."""
    # Admin creates org-wide channel
    resp = await client.post(
        "/api/v1/briefing/channels?org_wide=true",
        json=CHANNEL_PAYLOAD,
        headers=HEADERS,
    )
    channel_id = resp.json()["id"]

    # User clones it
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.post(
        f"/api/v1/briefing/channels/{channel_id}/clone",
        json={"name": "Mein Energie-Briefing"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["cloned_from_id"] == channel_id
    assert data["name"] == "Mein Energie-Briefing"


@pytest.mark.anyio
async def test_clone_personal_channel_fails(client, test_tenant):
    """Cannot clone a personal channel (only org channels)."""
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    # User creates personal channel
    resp = await client.post(
        "/api/v1/briefing/channels",
        json={**CHANNEL_PAYLOAD, "slug": "personal-ch"},
        headers=headers,
    )
    channel_id = resp.json()["id"]

    # Try to clone personal channel → should fail
    response = await client.post(
        f"/api/v1/briefing/channels/{channel_id}/clone",
        json={},
        headers=headers,
    )
    assert response.status_code == 403


# --- Per-User Scoping: Sources ---


@pytest.mark.anyio
async def test_create_org_source_as_admin(client, test_tenant):
    """Admin can create org-wide source with org_wide=true."""
    response = await client.post(
        "/api/v1/briefing/sources?org_wide=true",
        json=SOURCE_PAYLOAD,
        headers=HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] is None


@pytest.mark.anyio
async def test_create_personal_source(client, test_tenant):
    """Source created by user without org_wide belongs to the user."""
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.post(
        "/api/v1/briefing/sources",
        json={**SOURCE_PAYLOAD, "name": "Mein RSS"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id


@pytest.mark.anyio
async def test_user_sees_org_and_own_sources(client, test_tenant):
    """User should see org-wide sources plus their own personal sources."""
    # Admin creates org-wide source
    await client.post(
        "/api/v1/briefing/sources?org_wide=true",
        json=SOURCE_PAYLOAD,
        headers=HEADERS,
    )

    # Create a regular user
    token, user_id = await _create_auth_user(client)
    headers = _user_headers(token)

    # User creates personal source
    await client.post(
        "/api/v1/briefing/sources",
        json={**SOURCE_PAYLOAD, "name": "Mein RSS"},
        headers=headers,
    )

    # User should see both
    response = await client.get("/api/v1/briefing/sources", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    user_ids = [s["user_id"] for s in data]
    assert None in user_ids  # org-wide
    assert user_id in user_ids  # personal


@pytest.mark.anyio
async def test_user_cannot_modify_org_source(client, test_tenant):
    """Non-admin user cannot update an org-wide source."""
    resp = await client.post(
        "/api/v1/briefing/sources?org_wide=true",
        json=SOURCE_PAYLOAD,
        headers=HEADERS,
    )
    source_id = resp.json()["id"]

    token, _ = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.put(
        f"/api/v1/briefing/sources/{source_id}",
        json={"name": "Hacked"},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_user_cannot_delete_org_source(client, test_tenant):
    """Non-admin user cannot delete an org-wide source."""
    resp = await client.post(
        "/api/v1/briefing/sources?org_wide=true",
        json=SOURCE_PAYLOAD,
        headers=HEADERS,
    )
    source_id = resp.json()["id"]

    token, _ = await _create_auth_user(client)
    headers = _user_headers(token)

    response = await client.delete(
        f"/api/v1/briefing/sources/{source_id}", headers=headers
    )
    assert response.status_code == 403


# --- Personal Briefing ---


@pytest.mark.anyio
async def test_get_personal_settings_defaults(client, personal_user):
    """GET /personal/settings should create and return default settings."""
    response = await client.get("/api/v1/briefing/personal/settings", headers=HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "test-tenant"
    assert data["user_id"] == personal_user.id
    assert data["email_enabled"] is False
    assert data["calendar_enabled"] is False
    assert data["unread_only"] is True
    assert data["days_back"] == 1
    assert data["max_items"] == 8


@pytest.mark.anyio
async def test_update_personal_settings(client, personal_user):
    """PUT /personal/settings should update stored personal settings."""
    response = await client.put(
        "/api/v1/briefing/personal/settings",
        json={
            "email_enabled": True,
            "calendar_enabled": True,
            "days_back": 2,
            "max_items": 6,
            "delivery_time": "06:30",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email_enabled"] is True
    assert data["calendar_enabled"] is True
    assert data["days_back"] == 2
    assert data["max_items"] == 6
    assert data["delivery_time"] == "06:30"


@pytest.mark.anyio
async def test_list_personal_connections_empty(client, personal_user):
    """GET /personal/connections should return an empty list initially."""
    response = await client.get(
        "/api/v1/briefing/personal/connections",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_personal_oauth_authorize_microsoft_email(client, personal_user):
    """GET /personal/oauth/authorize should return a provider auth URL."""
    response = await client.get(
        "/api/v1/briefing/personal/oauth/authorize"
        "?provider=microsoft&integration_type=email",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "login.microsoftonline.com" in data["auth_url"]
    assert "Mail.Read" in data["auth_url"]


@pytest.mark.anyio
async def test_personal_oauth_callback_creates_connection(client, personal_user):
    """GET /personal/oauth/callback should store a personal connection."""
    from app.briefing.oauth import encrypt_token

    state = encrypt_token(
        {
            "tenant_id": "test-tenant",
            "user_id": personal_user.id,
            "provider": "google",
            "integration_type": "calendar",
            "flow": "personal",
        }
    )

    with (
        patch(
            "app.briefing.router._exchange_oauth_code",
            return_value={
                "access_token": "access-123",
                "refresh_token": "refresh-123",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.readonly openid email",
            },
        ),
        patch(
            "app.briefing.router._fetch_oauth_email",
            return_value="calendar@test.de",
        ),
    ):
        response = await client.get(
            f"/api/v1/briefing/personal/oauth/callback?code=fake-code&state={state}"
        )

    assert response.status_code == 200
    assert "Verbindung erfolgreich" in response.text

    list_response = await client.get(
        "/api/v1/briefing/personal/connections",
        headers=HEADERS,
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert len(data) == 1
    assert data[0]["provider"] == "google"
    assert data[0]["integration_type"] == "calendar"
    assert data[0]["connected_email"] == "calendar@test.de"
    assert data[0]["status"] == "connected"


@pytest.mark.anyio
async def test_disconnect_personal_connection(client, personal_user):
    """POST /personal/connections/{id}/disconnect should revoke the connection."""
    from app.briefing.oauth import encrypt_token

    state = encrypt_token(
        {
            "tenant_id": "test-tenant",
            "user_id": personal_user.id,
            "provider": "microsoft",
            "integration_type": "email",
            "flow": "personal",
        }
    )

    with (
        patch(
            "app.briefing.router._exchange_oauth_code",
            return_value={
                "access_token": "access-456",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
                "scope": "Mail.Read User.Read offline_access",
            },
        ),
        patch(
            "app.briefing.router._fetch_oauth_email",
            return_value="mail@test.de",
        ),
    ):
        await client.get(
            f"/api/v1/briefing/personal/oauth/callback?code=fake-code&state={state}"
        )

    connections_response = await client.get(
        "/api/v1/briefing/personal/connections",
        headers=HEADERS,
    )
    connection_id = connections_response.json()[0]["id"]

    response = await client.post(
        f"/api/v1/briefing/personal/connections/{connection_id}/disconnect",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == connection_id
    assert data["status"] == "revoked"


@pytest.mark.anyio
async def test_run_personal_briefing(client, personal_user):
    """POST /personal/run should fetch personal email and calendar items."""
    from app.briefing.oauth import encrypt_token
    from app.briefing.service import BriefingService
    from app.database import SessionLocal

    async with SessionLocal() as db:
        service = BriefingService(db)
        await service.update_personal_settings(
            "test-tenant",
            personal_user.id,
            {
                "email_enabled": True,
                "calendar_enabled": True,
                "days_back": 2,
                "max_items": 3,
            },
        )
        await service.upsert_personal_connection(
            tenant_id="test-tenant",
            user_id=personal_user.id,
            provider="microsoft",
            integration_type="email",
            encrypted_token=encrypt_token(
                {
                    "access_token": "email-token",
                    "refresh_token": "email-refresh",
                    "expires_at": 9999999999,
                }
            ),
            connected_email="mail@test.de",
            scopes=["Mail.Read"],
        )
        await service.upsert_personal_connection(
            tenant_id="test-tenant",
            user_id=personal_user.id,
            provider="google",
            integration_type="calendar",
            encrypted_token=encrypt_token(
                {
                    "access_token": "calendar-token",
                    "refresh_token": "calendar-refresh",
                    "expires_at": 9999999999,
                }
            ),
            connected_email="calendar@test.de",
            scopes=["Calendars.Read"],
        )
        await db.commit()

    with (
        patch(
            "app.briefing.service.fetch_emails",
            return_value=[
                {
                    "title": "Unread message",
                    "summary": "Bitte prüfen",
                    "url": "https://mail.test/1",
                    "found_at": "2026-03-13T07:00:00",
                    "metadata": {"is_unread": True},
                },
                {
                    "title": "Read message",
                    "summary": "Schon gelesen",
                    "url": "https://mail.test/2",
                    "found_at": "2026-03-13T06:00:00",
                    "metadata": {"is_unread": False},
                },
            ],
        ),
        patch(
            "app.briefing.service.fetch_calendar",
            return_value=[
                {
                    "title": "Daily Standup",
                    "summary": "Team meeting",
                    "url": "https://calendar.test/1",
                    "found_at": "2026-03-13T09:00:00",
                }
            ],
        ),
    ):
        response = await client.post(
            "/api/v1/briefing/personal/run",
            headers=HEADERS,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == personal_user.id
    assert data["sections"]["email"]["items_count"] == 1
    assert data["sections"]["calendar"]["items_count"] == 1
    assert data["errors"] == []


@pytest.mark.anyio
async def test_ai_module_setup_schema_briefing(client, personal_user):
    """GET /ai/modules/briefing/setup-schema should expose config, actions and enduser controls."""
    response = await client.get(
        "/api/v1/ai/modules/briefing/setup-schema",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["module"] == "briefing"
    assert "config_schema" in data
    assert any(
        item["key"] == "run_personal_briefing"
        for item in data["config_schema"]["actions"]
    )
    assert any(
        item["key"] == "email_enabled"
        for item in data["config_schema"]["enduser_controls"]
    )
    assert any(
        item["key"] == "microsoft_client_secret"
        and item["secret"] is True
        for item in data["config_schema"]["credentials"]
    )


@pytest.mark.anyio
async def test_ai_module_setup_schema_redacts_configured_secret(
    client, personal_user, monkeypatch, tmp_path
):
    """Configured AI credential secrets should only be exposed as redacted placeholders."""
    TenantService.clear_config_cache()
    monkeypatch.setattr(settings, "tenant_config_dir", str(tmp_path))
    (tmp_path / "test-tenant.env").write_text("microsoft_client_secret=top-secret\n")

    response = await client.get(
        "/api/v1/ai/modules/briefing/setup-schema",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    secret_field = next(
        item
        for item in data["config_schema"]["credentials"]
        if item["key"] == "microsoft_client_secret"
    )
    assert secret_field["value"] == "***configured***"
    assert secret_field["configured"] is True


@pytest.mark.anyio
async def test_ai_module_config_updates_system_credentials_via_tenant_config_path(
    client, personal_user, db_session, monkeypatch, tmp_path
):
    """AI module config updates should persist system credentials via tenant config and redact reads."""
    TenantService.clear_config_cache()
    monkeypatch.setattr(settings, "tenant_config_dir", str(tmp_path))

    response = await client.put(
        "/api/v1/ai/modules/briefing/config",
        json={
            "llm_provider": "ollama",
            "microsoft_client_id": "client-123",
            "microsoft_client_secret": "top-secret",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["config"]["llm_provider"] == "ollama"
    assert data["credentials"]["microsoft_client_id"] == "client-123"
    assert data["credentials"]["microsoft_client_secret"] == "***configured***"

    from app.models.tenant import Tenant

    tenant = (
        await db_session.execute(select(Tenant).where(Tenant.tenant_id == "test-tenant"))
    ).scalar_one()
    assert tenant.config["briefing"]["llm_provider"] == "ollama"
    assert tenant.config["microsoft_client_id"] == "client-123"
    assert tenant.config["microsoft_client_secret"] == "top-secret"

    env_contents = (tmp_path / "test-tenant.env").read_text()
    assert "microsoft_client_id=client-123" in env_contents
    assert "microsoft_client_secret=top-secret" in env_contents


# --- Speakers (XTTS Voice Cloning) ---


def _make_wav(duration_seconds: int = 10, sample_rate: int = 22050) -> bytes:
    """Generate a minimal valid WAV file with the given duration."""
    import struct
    import wave
    from io import BytesIO

    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        num_frames = sample_rate * duration_seconds
        wf.writeframes(struct.pack(f"<{num_frames}h", *([0] * num_frames)))
    return buf.getvalue()


@pytest.mark.anyio
async def test_list_speakers_empty(client, test_tenant):
    """GET /api/v1/briefing/speakers should return empty list when no speakers."""
    response = await client.get("/api/v1/briefing/speakers", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_upload_speaker(client, test_tenant, tmp_path):
    """POST /api/v1/briefing/speakers should create a speaker from WAV upload."""
    wav_bytes = _make_wav(duration_seconds=10)

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        response = await client.post(
            "/api/v1/briefing/speakers",
            data={"name": "Test-Sprecher", "language": "de", "description": "Test"},
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            headers=HEADERS,
        )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test-Sprecher"
    assert data["language"] == "de"
    assert data["duration_seconds"] == 10
    assert data["active"] is True


@pytest.mark.anyio
async def test_upload_speaker_too_short(client, test_tenant, tmp_path):
    """POST /api/v1/briefing/speakers should reject audio shorter than 6 seconds."""
    wav_bytes = _make_wav(duration_seconds=3)

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        response = await client.post(
            "/api/v1/briefing/speakers",
            data={"name": "Kurz", "language": "de"},
            files={"file": ("short.wav", wav_bytes, "audio/wav")},
            headers=HEADERS,
        )
    assert response.status_code == 400
    assert "zu kurz" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_speaker_too_long(client, test_tenant, tmp_path):
    """POST /api/v1/briefing/speakers should reject audio longer than 30 seconds."""
    wav_bytes = _make_wav(duration_seconds=35)

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        response = await client.post(
            "/api/v1/briefing/speakers",
            data={"name": "Lang", "language": "de"},
            files={"file": ("long.wav", wav_bytes, "audio/wav")},
            headers=HEADERS,
        )
    assert response.status_code == 400
    assert "zu lang" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_speaker_not_wav(client, test_tenant):
    """POST /api/v1/briefing/speakers should reject non-WAV files."""
    response = await client.post(
        "/api/v1/briefing/speakers",
        data={"name": "Bad", "language": "de"},
        files={"file": ("test.mp3", b"not-a-wav-file", "audio/mpeg")},
        headers=HEADERS,
    )
    assert response.status_code == 400
    assert "WAV" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_speaker(client, test_tenant, tmp_path):
    """DELETE /api/v1/briefing/speakers/{id} should delete the speaker."""
    wav_bytes = _make_wav(duration_seconds=10)

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        create_resp = await client.post(
            "/api/v1/briefing/speakers",
            data={"name": "Delete-Me", "language": "de"},
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            headers=HEADERS,
        )
    speaker_id = create_resp.json()["id"]

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        response = await client.delete(
            f"/api/v1/briefing/speakers/{speaker_id}", headers=HEADERS
        )
    assert response.status_code == 204

    # Verify speaker is gone
    list_resp = await client.get("/api/v1/briefing/speakers", headers=HEADERS)
    assert len(list_resp.json()) == 0


@pytest.mark.anyio
async def test_speaker_preview(client, test_tenant, tmp_path):
    """GET /api/v1/briefing/speakers/{id}/preview should return WAV audio."""
    wav_bytes = _make_wav(duration_seconds=10)

    with patch("app.briefing.service.settings") as mock_settings:
        mock_settings.speaker_upload_dir = str(tmp_path / "speakers")
        create_resp = await client.post(
            "/api/v1/briefing/speakers",
            data={"name": "Preview-Test", "language": "de"},
            files={"file": ("test.wav", wav_bytes, "audio/wav")},
            headers=HEADERS,
        )
    speaker_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/briefing/speakers/{speaker_id}/preview", headers=HEADERS
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


@pytest.mark.anyio
async def test_non_admin_cannot_upload_speaker(client, test_tenant):
    """Non-admin users should not be able to upload speakers."""
    token, _ = await _create_auth_user(client)
    headers = _user_headers(token)

    wav_bytes = _make_wav(duration_seconds=10)
    response = await client.post(
        "/api/v1/briefing/speakers",
        data={"name": "Test", "language": "de"},
        files={"file": ("test.wav", wav_bytes, "audio/wav")},
        headers=headers,
    )
    assert response.status_code == 403


@pytest.mark.anyio
async def test_channel_with_xtts_engine(client, test_tenant):
    """Channel should accept tts_engine and xtts_speaker_id fields."""
    payload = {
        **CHANNEL_PAYLOAD,
        "slug": "xtts-channel",
        "tts_engine": "xtts",
        "xtts_speaker_id": None,
    }
    response = await client.post(
        "/api/v1/briefing/channels", json=payload, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["tts_engine"] == "xtts"
    assert data["xtts_speaker_id"] is None


@pytest.mark.anyio
async def test_tts_service_engine_dispatch():
    """TTSService should dispatch to correct engine based on override."""
    from unittest.mock import AsyncMock, patch

    from app.briefing.tts import TTSService

    # Test Piper dispatch
    tts = TTSService(engine_override="piper")
    assert tts.engine == "piper"
    assert tts.is_available() is True

    # Test XTTS dispatch
    tts_xtts = TTSService(engine_override="xtts")
    assert tts_xtts.engine == "xtts"
    assert tts_xtts.is_available() is True

    # Test disabled
    tts_disabled = TTSService(engine_override="disabled")
    assert tts_disabled.engine == "disabled"
    assert tts_disabled.is_available() is False

    # Test XTTS synthesize calls _call_xtts
    tts_mock = TTSService(engine_override="xtts")
    with patch.object(tts_mock, "_call_xtts", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = b"fake-audio"
        result = await tts_mock.synthesize("Hallo Welt", "speaker_name", language="de")
        assert result == b"fake-audio"
        mock_call.assert_called_once_with("Hallo Welt", "speaker_name", "de")


# --- OAuth ---


@pytest.mark.anyio
async def test_oauth_authorize_redirect_microsoft(client, test_tenant):
    """GET /oauth/authorize should redirect to Microsoft consent screen."""
    # Create a calendar source first
    source_resp = await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "Kalender",
            "source_type": "calendar",
            "fetch_interval_hours": 24,
        },
        headers=HEADERS,
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    with patch("app.briefing.router.settings") as mock_settings:
        mock_settings.microsoft_client_id = "test-client-id"
        mock_settings.microsoft_tenant_id = "test-tenant-id"
        mock_settings.app_url = "http://localhost:8000"
        mock_settings.google_client_id = ""
        mock_settings.google_client_secret = ""
        mock_settings.microsoft_client_secret = ""

        response = await client.get(
            f"/api/v1/briefing/oauth/authorize?source_id={source_id}&provider=microsoft",
            headers=HEADERS,
        )
    assert response.status_code == 200
    auth_url = response.json()["auth_url"]
    assert "login.microsoftonline.com" in auth_url
    assert "test-client-id" in auth_url
    assert "Calendars.Read" in auth_url


@pytest.mark.anyio
async def test_oauth_authorize_redirect_google(client, test_tenant):
    """GET /oauth/authorize should redirect to Google consent screen."""
    source_resp = await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "Google Mail",
            "source_type": "email",
            "fetch_interval_hours": 24,
        },
        headers=HEADERS,
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    with patch("app.briefing.router.settings") as mock_settings:
        mock_settings.google_client_id = "google-test-id"
        mock_settings.app_url = "http://localhost:8000"
        mock_settings.microsoft_client_id = ""
        mock_settings.microsoft_client_secret = ""
        mock_settings.microsoft_tenant_id = ""
        mock_settings.google_client_secret = ""

        response = await client.get(
            f"/api/v1/briefing/oauth/authorize?source_id={source_id}&provider=google",
            headers=HEADERS,
        )
    assert response.status_code == 200
    auth_url = response.json()["auth_url"]
    assert "accounts.google.com" in auth_url
    assert "google-test-id" in auth_url
    assert "calendar.readonly" in auth_url


@pytest.mark.anyio
async def test_oauth_authorize_invalid_provider(client, test_tenant):
    """GET /oauth/authorize with invalid provider should return 422."""
    response = await client.get(
        "/api/v1/briefing/oauth/authorize?source_id=1&provider=invalid",
        headers=HEADERS,
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_oauth_disconnect(client, test_tenant):
    """POST /sources/{id}/oauth/disconnect should clear OAuth config."""
    # Create a source with OAuth config
    source_resp = await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "Connected Calendar",
            "source_type": "calendar",
            "fetch_interval_hours": 24,
            "config": {
                "oauth_provider": "microsoft",
                "oauth_token": "encrypted-data",
                "oauth_email": "user@test.com",
                "oauth_connected_at": "2026-02-24T12:00:00",
            },
        },
        headers=HEADERS,
    )
    assert source_resp.status_code == 201
    source_id = source_resp.json()["id"]

    # Verify OAuth connected
    get_resp = await client.get(
        f"/api/v1/briefing/sources/{source_id}", headers=HEADERS
    )
    assert get_resp.json()["oauth_connected"] is True
    assert get_resp.json()["oauth_email"] == "user@test.com"

    # Disconnect
    disc_resp = await client.post(
        f"/api/v1/briefing/sources/{source_id}/oauth/disconnect", headers=HEADERS
    )
    assert disc_resp.status_code == 200
    data = disc_resp.json()
    assert data["oauth_connected"] is False
    assert data["oauth_email"] is None


@pytest.mark.anyio
async def test_source_response_strips_oauth_token(client, test_tenant):
    """Source responses should not expose encrypted oauth_token."""
    source_resp = await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "Secret Source",
            "source_type": "calendar",
            "fetch_interval_hours": 24,
            "config": {
                "oauth_provider": "google",
                "oauth_token": "super-secret-encrypted-token",
                "oauth_email": "test@google.com",
                "days_back": 14,
            },
        },
        headers=HEADERS,
    )
    assert source_resp.status_code == 201
    data = source_resp.json()
    # Token should be stripped
    assert "oauth_token" not in (data.get("config") or {})
    # Other config keys should remain
    assert data["config"]["oauth_provider"] == "google"
    assert data["config"]["days_back"] == 14
    # Computed fields should be set
    assert data["oauth_connected"] is True
    assert data["oauth_email"] == "test@google.com"


@pytest.mark.anyio
async def test_source_list_includes_oauth_fields(client, test_tenant):
    """Source list should include oauth_connected and oauth_email fields."""
    await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "RSS Source",
            "source_type": "rss",
            "url": "https://example.com/rss",
            "fetch_interval_hours": 24,
        },
        headers=HEADERS,
    )
    await client.post(
        "/api/v1/briefing/sources",
        json={
            "name": "Calendar Source",
            "source_type": "calendar",
            "fetch_interval_hours": 24,
            "config": {
                "oauth_provider": "microsoft",
                "oauth_token": "encrypted",
                "oauth_email": "cal@test.com",
            },
        },
        headers=HEADERS,
    )

    response = await client.get("/api/v1/briefing/sources", headers=HEADERS)
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 2

    # Calendar source should have oauth fields
    cal = next(s for s in sources if s["source_type"] == "calendar")
    assert cal["oauth_connected"] is True
    assert cal["oauth_email"] == "cal@test.com"

    # RSS source should have default oauth fields
    rss = next(s for s in sources if s["source_type"] == "rss")
    assert rss["oauth_connected"] is False
    assert rss["oauth_email"] is None


@pytest.mark.anyio
async def test_calendar_fetcher_microsoft():
    """fetch_calendar should parse Microsoft Graph response."""
    from unittest.mock import AsyncMock, MagicMock

    from app.utils.source_fetchers import fetch_calendar

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {
                "subject": "Team Meeting",
                "bodyPreview": "Discuss project status",
                "webLink": "https://outlook.com/event/123",
                "start": {"dateTime": "2026-02-20T10:00:00"},
                "end": {"dateTime": "2026-02-20T11:00:00"},
            }
        ]
    }

    with patch("app.utils.source_fetchers.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance

        items = await fetch_calendar("fake-token", "microsoft", days_back=7)

    assert len(items) == 1
    assert items[0]["title"] == "Team Meeting"
    assert items[0]["summary"] == "Discuss project status"
    assert items[0]["url"] == "https://outlook.com/event/123"


@pytest.mark.anyio
async def test_email_fetcher_microsoft_with_keywords():
    """fetch_emails should filter by keywords for Microsoft."""
    from unittest.mock import AsyncMock, MagicMock

    from app.utils.source_fetchers import fetch_emails

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "value": [
            {
                "subject": "Solar Project Update",
                "bodyPreview": "Here is the latest on the solar installation...",
                "webLink": "https://outlook.com/msg/1",
                "receivedDateTime": "2026-02-20T14:00:00",
            },
            {
                "subject": "Lunch tomorrow?",
                "bodyPreview": "Want to grab lunch?",
                "webLink": "https://outlook.com/msg/2",
                "receivedDateTime": "2026-02-20T13:00:00",
            },
        ]
    }

    with patch("app.utils.source_fetchers.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance

        items = await fetch_emails(
            "fake-token", "microsoft", days_back=7, keywords=["solar"]
        )

    assert len(items) == 1
    assert items[0]["title"] == "Solar Project Update"


@pytest.mark.anyio
async def test_fetch_oauth_source_no_token():
    """_fetch_oauth_source should return empty list when no token."""
    from unittest.mock import AsyncMock, MagicMock

    from app.briefing.service import BriefingService

    mock_db = AsyncMock()
    service = BriefingService(mock_db)

    source = MagicMock()
    source.id = 1
    source.config = {}
    source.source_type = "calendar"

    result = await service._fetch_oauth_source(source)
    assert result == []


@pytest.mark.anyio
async def test_encrypt_decrypt_token():
    """encrypt_token and decrypt_token should be symmetric."""
    from app.briefing.oauth import decrypt_token, encrypt_token

    original = {
        "access_token": "test-access",
        "refresh_token": "test-refresh",
        "expires_at": 1234567890,
    }
    encrypted = encrypt_token(original)
    assert encrypted != str(original)
    decrypted = decrypt_token(encrypted)
    assert decrypted == original
