"""Tests for the assistant module."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.main import app

HEADERS = {"X-Tenant-ID": "test-tenant"}


async def _create_auth_user(client, email="assistant@test.de", role="user"):
    """Create a user and return (token, user_id)."""
    resp = await client.post(
        "/api/v1/auth/users",
        json={
            "email": email,
            "password": "testpass123",
            "display_name": "Test User",
            "role": role,
        },
        headers=HEADERS,
    )
    assert resp.status_code in (200, 201), f"User create failed: {resp.text}"
    user_id = resp.json()["id"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
        headers=HEADERS,
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    return token, user_id


def _user_headers(token):
    return {**HEADERS, "Authorization": f"Bearer {token}"}


# ── Profile ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_get_profile_creates_default(client, test_tenant):
    """GET /profile auto-creates a default profile."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/profile", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is True
    assert data["briefing_enabled"] is True
    assert data["llm_provider"] == "ollama"
    assert data["stt_provider"] == "faster-whisper"
    assert data["tts_provider"] == "piper"
    assert data["max_items_per_run"] == 30
    assert data["default_reply_mode"] == "draft"
    assert "voice_enabled" in data
    assert "autopilot_enabled" in data


@pytest.mark.anyio
async def test_update_profile(client, test_tenant):
    """PUT /profile updates fields."""
    token, _ = await _create_auth_user(client)
    # ensure profile exists
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    resp = await client.put(
        "/api/v1/assistant/profile",
        json={
            "voice_enabled": True,
            "llm_provider": "anthropic",
            "max_items_per_run": 50,
        },
        headers=_user_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_enabled"] is True
    assert data["llm_provider"] == "anthropic"
    assert data["max_items_per_run"] == 50
    # untouched fields remain
    assert data["active"] is True


# ── Rules ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rule_crud(client, test_tenant):
    """Full CRUD cycle for rules."""
    token, _ = await _create_auth_user(client)

    # Create
    resp = await client.post(
        "/api/v1/assistant/rules",
        json={
            "name": "Newsletter archivieren",
            "action_type": "archive",
            "risk_level": "low",
            "match_criteria_json": {"sender_domain": "newsletter.example.com"},
        },
        headers=_user_headers(token),
    )
    assert resp.status_code == 201
    rule = resp.json()
    rule_id = rule["id"]
    assert rule["name"] == "Newsletter archivieren"
    assert rule["enabled"] is True
    assert rule["origin"] == "manual"

    # List
    resp = await client.get(
        "/api/v1/assistant/rules", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Update
    resp = await client.put(
        f"/api/v1/assistant/rules/{rule_id}",
        json={"enabled": False, "risk_level": "medium"},
        headers=_user_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
    assert resp.json()["risk_level"] == "medium"

    # Delete
    resp = await client.delete(
        f"/api/v1/assistant/rules/{rule_id}",
        headers=_user_headers(token),
    )
    assert resp.status_code == 204

    # Verify deleted
    resp = await client.get(
        "/api/v1/assistant/rules", headers=_user_headers(token)
    )
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_rule_invalid_risk_level(client, test_tenant):
    """Creating a rule with invalid risk_level returns 400."""
    token, _ = await _create_auth_user(client)
    resp = await client.post(
        "/api/v1/assistant/rules",
        json={
            "name": "Bad Rule",
            "action_type": "label",
            "risk_level": "critical",
        },
        headers=_user_headers(token),
    )
    assert resp.status_code == 400


# ── Dashboard ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_dashboard_stats(client, test_tenant):
    """GET /dashboard returns stats."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/dashboard", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_items" in data
    assert "active_rules" in data
    assert "pending_actions" in data
    assert "connected_sources" in data
    assert data["total_items"] == 0


# ── Items (empty) ────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_items_empty(client, test_tenant):
    """GET /items returns empty list when no items."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/items", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_get_item_not_found(client, test_tenant):
    """GET /items/999 returns 404."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/items/999", headers=_user_headers(token)
    )
    assert resp.status_code == 404


# ── Pending Actions (empty) ──────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_actions_empty(client, test_tenant):
    """GET /actions/pending returns empty list."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/actions/pending", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Sources (empty, no connections yet) ──────────────────────────────


@pytest.mark.anyio
async def test_list_sources_empty(client, test_tenant):
    """GET /sources returns empty list."""
    token, _ = await _create_auth_user(client)
    resp = await client.get(
        "/api/v1/assistant/sources", headers=_user_headers(token)
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_add_source_invalid_connection(client, test_tenant):
    """POST /sources with nonexistent connection_id returns 404."""
    token, _ = await _create_auth_user(client)
    resp = await client.post(
        "/api/v1/assistant/sources",
        json={"connection_id": 99999},
        headers=_user_headers(token),
    )
    assert resp.status_code == 404


# ── Briefing Run ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_briefing_run_empty(client, test_tenant):
    """POST /briefing/run with no items returns empty briefing."""
    token, _ = await _create_auth_user(client)
    resp = await client.post(
        "/api/v1/assistant/briefing/run",
        json={},
        headers=_user_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items_processed"] == 0
    assert "briefing_text" in data
    assert data["generated_at"] is not None


# ── Classifier ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_classifier_importance():
    """Test rule-based importance classification."""
    from unittest.mock import MagicMock

    from app.assistant.classifier import AssistantClassifier

    item = MagicMock()
    item.title = "DRINGEND: Vertrag unterschreiben"
    item.sender = "chef@firma.de"
    item.item_type = "email"
    item.content_snippet = ""

    classifier = AssistantClassifier(MagicMock())
    result = classifier._estimate_importance(item)
    assert result == "high"


@pytest.mark.anyio
async def test_classifier_newsletter():
    """Test newsletter detection."""
    from unittest.mock import MagicMock

    from app.assistant.classifier import AssistantClassifier

    item = MagicMock()
    item.title = "Weekly Newsletter: Updates"
    item.sender = "newsletter@example.com"
    item.item_type = "email"
    item.content_snippet = ""

    classifier = AssistantClassifier(MagicMock())
    result = classifier._estimate_importance(item)
    assert result == "low"


# ── Rule Engine ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_rule_engine_matches():
    """Test rule matching logic."""
    from unittest.mock import MagicMock

    from app.assistant.rules import AssistantRuleEngine

    rule = MagicMock()
    rule.match_criteria_json = {"sender_domain": "newsletter.example.com"}
    rule.action_type = "archive"
    rule.risk_level = "low"
    rule.name = "Test Rule"
    rule.id = 1

    item = MagicMock()
    item.title = "Some newsletter"
    item.sender = "info@newsletter.example.com"
    item.content_snippet = "Content here"
    item.item_type = "email"

    engine = AssistantRuleEngine(MagicMock())
    assert engine._matches(rule, item) is True


@pytest.mark.anyio
async def test_rule_engine_no_match():
    """Test rule not matching."""
    from unittest.mock import MagicMock

    from app.assistant.rules import AssistantRuleEngine

    rule = MagicMock()
    rule.match_criteria_json = {"sender_domain": "newsletter.example.com"}

    item = MagicMock()
    item.title = "Regular email"
    item.sender = "boss@firma.de"
    item.content_snippet = ""
    item.item_type = "email"

    engine = AssistantRuleEngine(MagicMock())
    assert engine._matches(rule, item) is False


# ── Intake Dedup ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_intake_hash_consistency():
    """Test payload hashing is deterministic."""
    from app.assistant.intake import AssistantIntakeService

    payload1 = {"id": "123", "subject": "Test"}
    payload2 = {"subject": "Test", "id": "123"}

    hash1 = AssistantIntakeService._hash_payload(payload1)
    hash2 = AssistantIntakeService._hash_payload(payload2)
    assert hash1 == hash2

    hash3 = AssistantIntakeService._hash_payload({"id": "456"})
    assert hash1 != hash3
