"""Tests for the assistant module."""

from datetime import UTC, datetime

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
    assert data["llm_provider"] == "anthropic"
    assert data["llm_model"]
    assert data["stt_provider"] == "faster-whisper"
    assert data["tts_provider"] == "piper"
    assert data["max_items_per_run"] == 30
    assert data["default_reply_mode"] == "draft"
    assert data["autopilot_min_confidence"] == 0.85
    assert data["autopilot_max_rule_risk"] == "medium"
    assert data["suggestion_min_confidence"] == 0.7
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
            "autopilot_min_confidence": 0.9,
            "autopilot_max_rule_risk": "low",
            "suggestion_min_confidence": 0.8,
        },
        headers=_user_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["voice_enabled"] is True
    assert data["llm_provider"] == "anthropic"
    assert data["max_items_per_run"] == 50
    assert data["autopilot_min_confidence"] == 0.9
    assert data["autopilot_max_rule_risk"] == "low"
    assert data["suggestion_min_confidence"] == 0.8
    # untouched fields remain
    assert data["active"] is True


@pytest.mark.anyio
async def test_service_get_or_create_profile_sets_trust_defaults():
    """Service-created profile should include autopilot trust defaults."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.service import AssistantService

    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    async def _refresh(profile):
        return profile

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    svc = AssistantService(mock_db)
    profile = await svc.get_or_create_profile("test", 1)

    assert profile.autopilot_min_confidence == 0.85
    assert profile.autopilot_max_rule_risk == "medium"
    assert profile.suggestion_min_confidence == 0.7


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


@pytest.mark.anyio
async def test_service_list_categories_seeds_defaults_and_creates_project_category():
    """Category registry should seed fixed defaults and normalize project names."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.service import AssistantService

    mock_db = AsyncMock()

    def _exec_result(*scalars):
        result = MagicMock()
        result.scalars.return_value.all.return_value = scalars[0] if scalars else []
        result.scalar_one_or_none.return_value = scalars[0] if scalars else None
        result.scalar_one.return_value = scalars[0] if scalars else 0
        return result

    mock_db.execute.side_effect = [
        _exec_result([]),
        _exec_result(
            [
                *[
                    type(
                        "CategoryRow",
                        (),
                        {
                            "id": index + 1,
                            "tenant_id": "test",
                            "user_id": 1,
                            "name": entry["name"],
                            "category_type": "fixed",
                            "color": entry["color"],
                            "active": True,
                            "system_default": True,
                            "metadata_json": None,
                            "created_at": datetime.now(UTC),
                            "updated_at": datetime.now(UTC),
                        },
                    )()
                    for index, entry in enumerate(AssistantService.DEFAULT_FIXED_CATEGORIES)
                ]
            ]
        ),
    ]
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()

    svc = AssistantService(mock_db)

    categories = await svc.list_categories("test", 1)
    svc._ensure_default_categories = AsyncMock()
    svc._assert_category_name_available = AsyncMock()
    svc._ensure_project_category_capacity = AsyncMock()
    created = await svc.create_category(
        "test",
        1,
        {"name": "WebsiteRelaunch", "category_type": "project", "color": "teal"},
    )

    assert len(categories) == 8
    assert categories[0].system_default is True
    assert mock_db.add.call_count >= 9
    assert created.name == "Projekt: WebsiteRelaunch"
    assert created.category_type == "project"


@pytest.mark.anyio
async def test_service_delete_category_rejects_system_default():
    """Seeded fixed categories must not be deletable."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.models import AssistantCategoryRegistry
    from app.assistant.service import AssistantService
    from app.exceptions import ValidationError

    category = AssistantCategoryRegistry(
        id=5,
        tenant_id="test",
        user_id=1,
        name="Dringend",
        category_type="fixed",
        active=True,
        system_default=True,
    )
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = category
    mock_db.execute.return_value = result

    svc = AssistantService(mock_db)

    with pytest.raises(ValidationError):
        await svc.delete_category("test", 1, 5)


@pytest.mark.anyio
async def test_list_categories_router_returns_payload():
    """Router should return category payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    expected = [
        {
            "id": 1,
            "tenant_id": "test-tenant",
            "user_id": 1,
            "name": "Dringend",
            "category_type": "fixed",
            "color": "red",
            "active": True,
            "system_default": True,
            "metadata_json": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
    ]

    with patch(
        "app.assistant.service.AssistantService.list_categories",
        new=AsyncMock(return_value=expected),
    ):
        result = await assistant_router.list_categories(
            include_inactive=False,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=AsyncMock(),
        )

    assert len(result) == 1
    assert result[0]["name"] == "Dringend"


@pytest.mark.anyio
async def test_review_waiting_router_returns_payload():
    """Router should return waiting-review payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    expected = [
        {
            "source_id": 2,
            "connection_id": 11,
            "mailbox_address": "team@test.de",
            "status": "WARTEN",
            "message_id": "msg-1",
            "thread_id": "thread-1",
            "subject": "Rueckfrage Kunde",
            "sender": "kunde@test.de",
            "received_at": datetime.now(UTC),
            "snippet": "Bitte Rueckmeldung",
            "is_unread": False,
            "has_attachments": False,
        }
    ]

    with patch(
        "app.assistant.service.AssistantService.review_waiting",
        new=AsyncMock(return_value=expected),
    ):
        result = await assistant_router.review_waiting(
            source_id=2,
            mailbox=None,
            older_than_days=5,
            limit=10,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=AsyncMock(),
        )

    assert len(result) == 1
    assert result[0]["status"] == "WARTEN"


@pytest.mark.anyio
async def test_review_stale_todos_router_returns_payload():
    """Router should return TODO-review payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    expected = [
        {
            "source_id": 2,
            "connection_id": 11,
            "mailbox_address": "team@test.de",
            "status": "TODO",
            "message_id": "msg-2",
            "thread_id": "thread-2",
            "subject": "Angebot pruefen",
            "sender": "vertrieb@test.de",
            "received_at": datetime.now(UTC),
            "snippet": "Bitte priorisieren",
            "is_unread": True,
            "has_attachments": True,
        }
    ]

    with patch(
        "app.assistant.service.AssistantService.review_stale_todos",
        new=AsyncMock(return_value=expected),
    ):
        result = await assistant_router.review_stale_todos(
            source_id=2,
            mailbox=None,
            older_than_days=7,
            limit=10,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=AsyncMock(),
        )

    assert len(result) == 1
    assert result[0]["status"] == "TODO"


@pytest.mark.anyio
async def test_triage_batch_router_returns_payload():
    """Router should return bounded triage batch payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    expected = [
        {
            "source_id": 2,
            "connection_id": 11,
            "mailbox_address": "team@test.de",
            "status": "INBOX",
            "message_id": "msg-3",
            "thread_id": "thread-3",
            "subject": "Neue Anfrage",
            "sender": "lead@test.de",
            "received_at": datetime.now(UTC),
            "snippet": "Interesse an Demo",
            "is_unread": True,
            "has_attachments": False,
        }
    ]

    with patch(
        "app.assistant.service.AssistantService.triage_batch",
        new=AsyncMock(return_value=expected),
    ):
        result = await assistant_router.triage_batch(
            source_id=2,
            mailbox=None,
            limit=10,
            unread_only=True,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=AsyncMock(),
        )

    assert len(result) == 1
    assert result[0]["status"] == "INBOX"


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


@pytest.mark.anyio
async def test_send_draft_router_maps_provider_failure_to_http_502():
    """Router should translate draft-send provider failures into HTTP 502."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from app.assistant import router as assistant_router
    from app.exceptions import ExternalServiceError

    db = AsyncMock()
    db.rollback = AsyncMock()

    with patch(
        "app.assistant.service.AssistantService.send_draft",
        new=AsyncMock(side_effect=ExternalServiceError("Assistant-Provider", "send")),
    ):
        with pytest.raises(HTTPException) as exc:
            await assistant_router.send_draft(
                15,
                tenant_id="test-tenant",
                user=SimpleNamespace(id=1),
                db=db,
            )

    assert exc.value.status_code == 502
    assert exc.value.detail == "Fehler bei Assistant-Provider: send"
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_execute_pending_intent_router_maps_provider_failure_to_http_502():
    """Router should translate pending-intent provider failures into HTTP 502."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from app.assistant import router as assistant_router
    from app.exceptions import ExternalServiceError

    db = AsyncMock()
    db.rollback = AsyncMock()

    with patch(
        "app.assistant.service.AssistantService.execute_pending_intent",
        new=AsyncMock(
            side_effect=ExternalServiceError("Assistant-Provider", "pending")
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await assistant_router.execute_pending_intent(
                22,
                tenant_id="test-tenant",
                user=SimpleNamespace(id=1),
                db=db,
            )

    assert exc.value.status_code == 502
    assert exc.value.detail == "Fehler bei Assistant-Provider: pending"
    db.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_undo_action_router_returns_payload():
    """Router should return the undo log payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    db = AsyncMock()
    db.commit = AsyncMock()
    now = datetime.now(UTC)
    undo_log = SimpleNamespace(
        id=31,
        tenant_id="test-tenant",
        user_id=1,
        conversation_id=9,
        connection_id=19,
        draft_id=None,
        pending_intent_id=41,
        action_type="mark_read",
        status="undone",
        can_undo=True,
        undone_at=now,
        target_ref_json={"email_id": "msg-1"},
        before_state_json={"is_read": False},
        after_state_json={"is_read": True},
        metadata_json={"source": "voice"},
        created_at=now,
        updated_at=now,
    )

    with patch(
        "app.assistant.service.AssistantService.undo_action",
        new=AsyncMock(return_value=undo_log),
    ):
        result = await assistant_router.undo_action(
            31,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=db,
        )

    assert result.id == 31
    assert result.action_type == "mark_read"
    assert result.status == "undone"
    assert result.pending_intent_id == 41
    db.commit.assert_awaited_once()


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


# ── Intake with mock provider ────────────────────────────────────────


@pytest.mark.anyio
async def test_intake_ingest_messages(client, test_tenant):
    """Test ingesting MailMessageRef objects into events + items."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock

    from app.assistant.intake import AssistantIntakeService
    from app.integrations.types import MailMessageRef

    # Create user + ensure profile
    token, user_id = await _create_auth_user(client)
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    # We need a real DB session — use the briefing run endpoint instead
    # to test the full pipeline indirectly. For unit-level intake, we mock.
    messages = [
        MailMessageRef(
            provider_message_id="msg-001",
            subject="Wichtige Nachricht",
            from_email="boss@firma.de",
            received_at=datetime.now(timezone.utc),
            is_unread=True,
            snippet="Bitte sofort antworten",
            thread_id="thread-001",
            raw={"id": "msg-001", "subject": "Wichtige Nachricht"},
        ),
        MailMessageRef(
            provider_message_id="msg-002",
            subject="Newsletter August",
            from_email="newsletter@example.com",
            received_at=datetime.now(timezone.utc),
            is_unread=True,
            snippet="Neuigkeiten aus dem Monat",
            thread_id="thread-002",
            raw={"id": "msg-002", "subject": "Newsletter August"},
        ),
    ]

    # Mock db session
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: None))
    mock_db.add = lambda x: None
    mock_db.flush = AsyncMock()

    intake = AssistantIntakeService(mock_db)
    events_created, items_created = await intake.ingest_messages(
        tenant_id="test-tenant",
        user_id=user_id,
        connection_id=1,
        messages=messages,
    )

    # Both messages should be new (mock returns None for existing check)
    assert events_created == 2
    assert items_created == 2


@pytest.mark.anyio
async def test_intake_token_refresh_needed():
    """Test that _ensure_access_token detects expired tokens."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.assistant.intake import AssistantIntakeService
    from app.assistant.models import IntegrationConnection

    conn = MagicMock(spec=IntegrationConnection)
    conn.id = 1
    conn.provider = "microsoft_graph"
    conn.encrypted_token = "encrypted_data"

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    intake = AssistantIntakeService(mock_db)

    # Token that expired 1 hour ago
    expired_token_data = {
        "access_token": "old_token",
        "refresh_token": "refresh_123",
        "expires_at": 0,  # way in the past
    }
    refreshed_data = {
        "access_token": "new_token",
        "expires_in": 3600,
    }

    with (
        patch("app.integrations.oauth.decrypt_token", return_value=expired_token_data),
        patch("app.integrations.oauth.encrypt_token", return_value="new_encrypted"),
        patch.object(intake, "_refresh_token", return_value=refreshed_data) as mock_refresh,
    ):
        token = await intake._ensure_access_token(conn)

    assert token == "new_token"
    mock_refresh.assert_called_once_with("microsoft_graph", "refresh_123")
    assert conn.encrypted_token == "new_encrypted"


# ── Voice Chat ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_voice_chat_no_source(client, test_tenant):
    """POST /voice/chat without connected source returns 400."""
    token, _ = await _create_auth_user(client, email="voice1@test.de")
    # Ensure profile exists
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    resp = await client.post(
        "/api/v1/assistant/voice/chat",
        data={"text": "Hallo", "tts_enabled": "false"},
        headers=_user_headers(token),
    )
    assert resp.status_code == 400
    assert "Kein Mailkonto" in resp.json()["detail"]


@pytest.mark.anyio
async def test_voice_chat_no_input(client, test_tenant):
    """POST /voice/chat without text or audio returns 400."""
    token, _ = await _create_auth_user(client, email="voice2@test.de")
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    resp = await client.post(
        "/api/v1/assistant/voice/chat",
        data={},
        headers=_user_headers(token),
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_voice_transcribe_requires_audio(client, test_tenant):
    """POST /voice/transcribe without audio returns 422."""
    token, _ = await _create_auth_user(client, email="voice3@test.de")

    resp = await client.post(
        "/api/v1/assistant/voice/transcribe",
        headers=_user_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_voice_tts_no_text(client, test_tenant):
    """POST /voice/tts without text returns 400."""
    token, _ = await _create_auth_user(client, email="voice4@test.de")
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    resp = await client.post(
        "/api/v1/assistant/voice/tts",
        json={"text": ""},
        headers=_user_headers(token),
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_stt_service_init():
    """STTService initializes with correct provider."""
    from app.assistant.stt import STTService

    stt = STTService(provider="faster-whisper")
    assert stt.provider == "faster-whisper"

    stt2 = STTService(provider="openai")
    assert stt2.provider == "openai"


@pytest.mark.anyio
async def test_voice_tool_executor_context():
    """VoiceToolExecutor manages context correctly."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {
                "id": "msg-1",
                "subject": "Test 1",
                "sender": "a@b.com",
                "snippet": "Hi",
                "summary": "Kurze Zusammenfassung 1",
            },
            {
                "id": "msg-2",
                "subject": "Test 2",
                "sender": "c@d.com",
                "snippet": "Hello",
                "summary": "Kurze Zusammenfassung 2",
            },
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=1,
        connection_id=1,
    )

    # Test read_email from context — shows position
    result = await executor._tool_read_email({"email_index": 2})
    assert "Test 2" in result
    assert "2 von 2" in result  # position info
    assert "Kurzfassung: Kurze Zusammenfassung 2" in result
    assert context["current_email_index"] == 2
    assert context["current_email_id"] == "msg-2"

    # Test next/previous
    result = await executor._tool_previous_email({})
    assert context["current_email_index"] == 1

    result = await executor._tool_next_email({})
    assert context["current_email_index"] == 2

    # Test boundary — at end of list triggers refresh path
    executor._tool_list_emails = AsyncMock(return_value="Liste aktualisiert")
    result = await executor._tool_next_email({})
    executor._tool_list_emails.assert_awaited_once()
    assert context["current_email_index"] == 1


@pytest.mark.anyio
async def test_voice_read_email_uses_summary_helper():
    """read_email should use the voice summary helper and cache the result."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Status", "sender": "chef@test.de", "snippet": "Bitte sende ein Update"}
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._summarize_email_for_voice = AsyncMock(
        return_value="Dein Chef bittet kurz um ein Status-Update."
    )

    result = await executor._tool_read_email({"email_index": 1})

    assert "Kurzfassung: Dein Chef bittet kurz um ein Status-Update." in result
    executor._summarize_email_for_voice.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_summarize_inbox_uses_existing_context():
    """Inbox overview should summarize the current email list without reloading."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {
                "id": "msg-1",
                "subject": "Status",
                "sender": "chef@test.de",
                "snippet": "Bitte sende ein Update",
                "is_unread": True,
                "mailbox": "info@test.de",
            },
            {
                "id": "msg-2",
                "subject": "LinkedIn",
                "sender": "jobs@linkedin.com",
                "snippet": "Profilaufrufe",
                "is_unread": False,
                "mailbox": "info@test.de",
            },
        ]
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._summarize_email_for_voice = AsyncMock(
        side_effect=[
            "Der Chef moechte ein Status-Update.",
            "LinkedIn meldet neue Profilaufrufe.",
        ]
    )

    result = await executor._tool_summarize_inbox({"limit": 2})

    assert result.startswith("Ueberblick ueber 2 Emails:")
    assert "chef@test.de (info@test.de) — Status [NEU]" in result
    assert "LinkedIn meldet neue Profilaufrufe." in result


@pytest.mark.anyio
async def test_voice_summarize_inbox_refreshes_when_requested():
    """Inbox overview should refresh the email list first when requested."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    async def load_list(_args):
        context["email_list"] = [
            {
                "id": "msg-1",
                "subject": "Neu",
                "sender": "a@b.com",
                "snippet": "Hi",
                "is_unread": True,
            }
        ]
        return "Liste geladen"

    executor._tool_list_emails = AsyncMock(side_effect=load_list)
    executor._summarize_email_for_voice = AsyncMock(return_value="Kurze Zusammenfassung.")

    result = await executor._tool_summarize_inbox({"refresh": True, "limit": 1})

    assert result.startswith("Ueberblick ueber 1 Emails:")
    executor._tool_list_emails.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_undo_last_action_uses_latest_undoable_log():
    """Voice undo tool should execute the latest undoable action from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=77,
    )

    matching = SimpleNamespace(
        id=41,
        conversation_id=77,
        action_type="move_email",
        target_ref_json={"subject": "LinkedIn Digest"},
    )
    older = SimpleNamespace(
        id=40,
        conversation_id=12,
        action_type="discard_draft",
        target_ref_json={"draft_id": 5},
    )

    with patch("app.assistant.service.AssistantService.list_undo_logs", new=AsyncMock(return_value=[older, matching])) as list_mock:
        with patch("app.assistant.service.AssistantService.undo_action", new=AsyncMock(return_value=matching)) as undo_mock:
            result = await executor._tool_undo_last_action({})

    assert "Rueckgaengig gemacht: move_email fuer LinkedIn Digest." == result
    list_mock.assert_awaited_once()
    undo_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_cancel_pending_action_uses_service_and_clears_context():
    """Voice cancel should cancel the current pending confirmation and clear it."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {"pending_confirmation": {"id": 55, "action": "delete_email"}}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    with patch(
        "app.assistant.service.AssistantService.cancel_pending_intent",
        new=AsyncMock(),
    ) as cancel_mock:
        result = await executor._tool_cancel_pending_action({})

    assert result == "Aktion 'delete_email' wurde abgebrochen."
    assert context.get("pending_confirmation") is None
    cancel_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_cancel_pending_action_without_pending():
    """Voice cancel should handle missing pending confirmation gracefully."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_cancel_pending_action({})

    assert result == "Es gibt keine offene bestaetigungspflichtige Aktion."


@pytest.mark.anyio
async def test_voice_undo_last_cleanup_uses_service():
    """Voice cleanup undo should call the central service method."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    with patch(
        "app.assistant.service.AssistantService.undo_last_cleanup_batch",
        new=AsyncMock(
            return_value={
                "pending_intent_id": 500,
                "undone_count": 1,
                "total_batch_logs": 2,
            }
        ),
    ) as undo_mock:
        result = await executor._tool_undo_last_cleanup({})

    assert "Cleanup-Batch #500" in result
    assert "1 von 2 Aktionen" in result
    undo_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_explain_email_rules_lists_matching_rules():
    """Voice rule explanation should describe matching active rules for the current email."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={
            "email_list": [
                {
                    "id": "msg-1",
                    "subject": "LinkedIn Suchanfragen",
                    "sender": "jobs@linkedin.com",
                    "snippet": "Sie wurden in 10 Suchanfragen gefunden",
                    "mailbox": "info@test.de",
                }
            ],
            "current_email_index": 1,
        },
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._load_cleanup_rules = AsyncMock(
        return_value=[
            SimpleNamespace(
                name="LinkedIn nach Unwichtig",
                action_type="move",
                action_payload_json={"target": "Unwichtig"},
                risk_level="low",
                match_criteria_json={"sender_contains": "linkedin.com"},
            )
        ]
    )

    result = await executor._tool_explain_email_rules({})

    assert "passen 1 aktive Regeln" in result
    assert "LinkedIn nach Unwichtig: move -> Unwichtig" in result


@pytest.mark.anyio
async def test_voice_explain_email_rules_without_match():
    """Voice rule explanation should say when no active rule matches the email."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={
            "email_list": [
                {
                    "id": "msg-1",
                    "subject": "Projekt X",
                    "sender": "chef@test.de",
                    "snippet": "Bitte sende ein Update",
                }
            ],
            "current_email_index": 1,
        },
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._load_cleanup_rules = AsyncMock(
        return_value=[
            SimpleNamespace(
                name="Newsletter archivieren",
                action_type="move",
                action_payload_json={"target": "Archiv"},
                risk_level="low",
                match_criteria_json={"sender_contains": "newsletter"},
            )
        ]
    )

    result = await executor._tool_explain_email_rules({})

    assert result == "Auf diese Email passt aktuell keine aktive Regel."


@pytest.mark.anyio
async def test_voice_set_and_clear_active_mailbox():
    """Voice mailbox scope should be settable and clearable in context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[(object(), "token", "info@test.de")]
    )

    set_result = await executor._tool_set_active_mailbox({"mailbox": "info@test.de"})
    clear_result = await executor._tool_clear_active_mailbox({})

    assert set_result == "Postfach 'info@test.de' ist jetzt aktiv."
    assert clear_result.startswith("Mailbox-Scope fuer 'info@test.de'")
    assert executor.context.get("active_mailbox") is None


@pytest.mark.anyio
async def test_voice_resolve_mailbox_scope_uses_active_mailbox():
    """Mailbox-sensitive tools should fall back to the active mailbox scope."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={"active_mailbox": "info@test.de"},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    assert executor._resolve_mailbox_scope() == "info@test.de"
    assert executor._resolve_mailbox_scope(all_mailboxes=True) is None
    assert executor._resolve_mailbox_scope("sales@test.de") == "sales@test.de"


@pytest.mark.anyio
async def test_voice_list_emails_uses_active_mailbox_scope():
    """list_emails should resolve the active mailbox via the scoped connection helper."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fallback-token",
        mailbox="primary@test.de",
        context={"active_mailbox": "shared@test.de"},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (SimpleNamespace(id=77), "token-shared", "shared@test.de")
        ]
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {
                "id": "msg-1",
                "conversationId": "thread-1",
                "subject": "Shared Mail",
                "from": {"emailAddress": {"address": "boss@test.de"}},
                "receivedDateTime": "2026-03-15T08:00:00+00:00",
                "isRead": False,
                "bodyPreview": "Bitte kurz pruefen",
                "parentFolderId": "inbox",
                "hasAttachments": False,
            }
        ]
    }

    from unittest.mock import patch

    with patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=mock_client,
    ):
        result = await executor._tool_list_emails({"limit": 5})

    assert "Shared Mail" in result
    assert executor.context["email_list"][0]["mailbox"] == "shared@test.de"
    mock_client.get.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_triage_batch_clamps_limit_to_ten():
    """Batch triage must never load more than 10 mails per turn."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._tool_list_emails = AsyncMock(return_value="1. Mail A\n2. Mail B")

    result = await executor._tool_triage_batch({"limit": 25})

    executor._tool_list_emails.assert_awaited_once_with({"limit": 10, "unread_only": False})
    assert "naechsten 10" in result


@pytest.mark.anyio
async def test_voice_review_waiting_uses_status_folder_policy():
    """Waiting review should read the mapped WARTEN folder and summarize old entries."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_scoped_connection = AsyncMock(return_value=(12, "token", "team@test.de"))
    service = AsyncMock()
    service.get_mailbox_policy_by_connection = AsyncMock(
        return_value={
            "status_folders": {
                "WARTEN": {"folder_id": "wait-folder"}
            }
        }
    )
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {
                "id": "msg-1",
                "conversationId": "thread-1",
                "subject": "Follow-up offen",
                "from": {"emailAddress": {"address": "kunde@test.de"}},
                "receivedDateTime": "2026-03-01T08:00:00+00:00",
                "bodyPreview": "Wie ist der Stand?",
            }
        ]
    }

    with patch("app.assistant.tool_executor.AssistantService", return_value=service), patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=mock_client,
    ):
        result = await executor._tool_review_waiting({"older_than_days": 5})

    assert "Review fuer WARTEN-Mails" in result
    assert executor.context["waiting_review"][0]["id"] == "msg-1"


@pytest.mark.anyio
async def test_voice_review_stale_todos_uses_status_folder_policy():
    """TODO review should read the mapped TODO folder and summarize old entries."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_scoped_connection = AsyncMock(return_value=(12, "token", "team@test.de"))
    service = AsyncMock()
    service.get_mailbox_policy_by_connection = AsyncMock(
        return_value={
            "status_folders": {
                "TODO": {"folder_id": "todo-folder"}
            }
        }
    )
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {
                "id": "msg-2",
                "conversationId": "thread-2",
                "subject": "Angebot finalisieren",
                "from": {"emailAddress": {"address": "chef@test.de"}},
                "receivedDateTime": "2026-03-01T08:00:00+00:00",
                "bodyPreview": "Bitte heute noch erledigen.",
            }
        ]
    }

    with patch("app.assistant.tool_executor.AssistantService", return_value=service), patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=mock_client,
    ):
        result = await executor._tool_review_stale_todos({"older_than_days": 7})

    assert "Review fuer alte TODO-Mails" in result
    assert executor.context["todo_review"][0]["id"] == "msg-2"


@pytest.mark.anyio
async def test_voice_move_intent_uses_scoped_connection_id_from_email_mailbox():
    """Pending intents for scoped mailbox emails should carry the resolved connection ID."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {
                "id": "msg-1",
                "subject": "Test",
                "sender": "a@b.com",
                "snippet": "Hi",
                "mailbox": "shared@test.de",
                "parent_folder_id": "folder-inbox",
            },
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 111
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fallback-token",
        mailbox="primary@test.de",
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=7,
        connection_id=11,
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[(SimpleNamespace(id=77), "token-shared", "shared@test.de")]
    )

    result = await executor._tool_move_email({"email_index": 1, "folder": "Archiv"})

    assert "BESTAETIGUNG" in result
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].connection_id == 77


@pytest.mark.anyio
async def test_voice_set_and_clear_active_folder():
    """Voice folder scope should be settable and clearable in context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._resolve_folder_id = AsyncMock(return_value="folder-123")

    set_result = await executor._tool_set_active_folder({"folder": "Archiv"})
    clear_result = await executor._tool_clear_active_folder({})

    assert set_result == "Ordner 'Archiv' ist jetzt aktiv."
    assert clear_result == "Ordner-Scope fuer 'Archiv' wurde aufgehoben."
    assert executor.context.get("active_folder_name") is None
    assert executor.context.get("active_folder_id") is None


@pytest.mark.anyio
async def test_voice_list_emails_uses_active_folder_scope():
    """list_emails should use the active folder and keep it in context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {"active_folder_name": "Unwichtig", "active_folder_id": "folder-9"}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {
                "id": "msg-1",
                "conversationId": "thread-1",
                "subject": "LinkedIn",
                "from": {"emailAddress": {"address": "jobs@linkedin.com"}},
                "receivedDateTime": "2026-03-15T08:00:00+00:00",
                "isRead": False,
                "bodyPreview": "Profilaufrufe",
                "parentFolderId": "folder-9",
                "hasAttachments": False,
            }
        ]
    }
    executor._get_graph_client = lambda: mock_client

    result = await executor._tool_list_emails({"limit": 5})

    assert result.startswith("Ordner Unwichtig:")
    assert "jobs@linkedin.com" in result
    assert executor.context["email_list"][0]["parent_folder_id"] == "folder-9"


@pytest.mark.anyio
async def test_voice_list_rule_suggestions_stores_context():
    """Voice tool should expose learned rule suggestions in the current context."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    suggestions = [
        {
            "name": "LinkedIn nach Unwichtig",
            "reason": "3x von LinkedIn nach Unwichtig verschoben",
            "action_type": "move",
            "action_payload": {"target": "Unwichtig"},
        }
    ]

    with patch(
        "app.assistant.learning.AssistantLearningService.suggest_rules",
        new=AsyncMock(return_value=suggestions),
    ):
        result = await executor._tool_list_rule_suggestions({})

    assert "LinkedIn nach Unwichtig" in result
    assert executor.context["rule_suggestions"] == suggestions


@pytest.mark.anyio
async def test_voice_apply_rule_suggestion_uses_context_index():
    """Voice tool should apply a selected suggestion from context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "rule_suggestions": [
            {
                "name": "LinkedIn nach Unwichtig",
                "reason": "3x von LinkedIn nach Unwichtig verschoben",
                "action_type": "move",
                "action_payload": {"target": "Unwichtig"},
            }
        ]
    }
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    with patch(
        "app.assistant.learning.AssistantLearningService.apply_suggestion",
        new=AsyncMock(return_value=SimpleNamespace(name="LinkedIn nach Unwichtig")),
    ) as apply_mock:
        result = await executor._tool_apply_rule_suggestion({"suggestion_index": 1})

    assert result == "Regel 'LinkedIn nach Unwichtig' wurde uebernommen."
    apply_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_service_conversation_create():
    """VoiceService creates a new conversation."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.voice import VoiceService

    mock_db = AsyncMock()

    # Mock flush to set ID on added objects
    added_objects = []
    original_add = mock_db.add

    def track_add(obj):
        obj.id = 99
        added_objects.append(obj)

    mock_db.add = track_add
    mock_db.flush = AsyncMock()

    # Mock execute for select to return None (no existing conversation)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    svc = VoiceService(mock_db)
    conv = await svc._get_or_create_conversation("test-tenant", 1, None)
    assert conv.channel == "voice"
    assert conv.state == "active"
    assert conv.context_json is not None


# ── Fix Verification Tests ──────────────────────────────────────────


@pytest.mark.anyio
async def test_pending_actions_only_suggested(client, test_tenant):
    """Fix 3: list_pending_actions should only return 'suggested' actions, not 'queued'."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.service import AssistantService

    # Create mock DB that tracks the query
    mock_db = AsyncMock()
    captured_queries = []

    async def capture_execute(query):
        compiled = query.compile(compile_kwargs={"literal_binds": True})
        captured_queries.append(str(compiled))
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = capture_execute

    svc = AssistantService(mock_db)
    await svc.list_pending_actions("test", 1)

    # Verify only 'suggested' is queried, NOT 'queued'
    assert len(captured_queries) == 1
    query_str = captured_queries[0]
    assert "suggested" in query_str
    assert "queued" not in query_str


@pytest.mark.anyio
async def test_approve_rejects_queued(client, test_tenant):
    """Fix 3: approve should only work on 'suggested', not 'queued'."""
    token, _ = await _create_auth_user(client, email="fix3@test.de")
    await client.get("/api/v1/assistant/profile", headers=_user_headers(token))

    # We can't easily create an action via API without items,
    # so test the service layer directly
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.models import AssistantAction
    from app.assistant.service import AssistantService

    mock_action = MagicMock(spec=AssistantAction)
    mock_action.status = "queued"
    mock_action.id = 1

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_action

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    svc = AssistantService(mock_db)
    with pytest.raises(Exception, match="kann nicht freigegeben werden"):
        await svc.approve_action("test", 1, 1)


@pytest.mark.anyio
async def test_action_not_implemented_status():
    """Fix 2: unimplemented actions should get 'not_implemented' status."""
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.actions import AssistantActionService
    from app.assistant.models import AssistantAction

    mock_action = MagicMock(spec=AssistantAction)
    mock_action.action_type = "delete"
    mock_action.item_id = 1
    mock_action.id = 1
    mock_action.status = "queued"
    mock_action.created_at = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = MagicMock()
    mock_result.scalars.return_value.__iter__ = lambda s: iter([mock_action])
    mock_result.scalars.return_value.all.return_value = [mock_action]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    svc = AssistantActionService(mock_db)
    executed = await svc.process_queued_actions("test", 1)

    # Should NOT be in executed list
    assert len(executed) == 0
    # Should be marked as not_implemented
    assert mock_action.status == "not_implemented"
    assert "nicht implementiert" in mock_action.error_message.lower() or "provider" in mock_action.error_message.lower()


@pytest.mark.anyio
async def test_oauth_shared_layer_imports():
    """Fix 4: verify oauth functions are importable from shared layer."""
    from app.integrations.oauth import (
        decrypt_token,
        encrypt_token,
        exchange_oauth_code,
        fetch_oauth_email,
        oauth_scope,
        refresh_google_token,
        refresh_microsoft_token,
    )

    # Verify encrypt/decrypt roundtrip
    test_data = {"access_token": "test123", "expires_at": 99999}
    encrypted = encrypt_token(test_data)
    decrypted = decrypt_token(encrypted)
    assert decrypted == test_data

    # Verify scope helper
    assert "Mail.Read" in oauth_scope("microsoft", "email")
    assert "gmail.readonly" in oauth_scope("google", "email")


@pytest.mark.anyio
async def test_briefing_oauth_backwards_compat():
    """Fix 4: briefing.oauth re-exports should still work."""
    from app.briefing.oauth import (
        decrypt_token,
        encrypt_token,
        refresh_google_token,
        refresh_microsoft_token,
    )

    # Verify they point to the same functions
    from app.integrations.oauth import decrypt_token as shared_decrypt
    from app.integrations.oauth import encrypt_token as shared_encrypt

    assert encrypt_token is shared_encrypt
    assert decrypt_token is shared_decrypt


@pytest.mark.anyio
async def test_voice_delete_requires_confirmation():
    """Fix 1 (voice): delete_email without confirmed=True returns confirmation request."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Wichtig", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    # Without confirmation — should NOT delete
    result = await executor._tool_delete_email({"email_index": 1})
    assert "BESTAETIGUNG" in result
    assert context.get("pending_confirmation") is not None
    assert context["pending_confirmation"]["action"] == "delete_email"
    assert "pending_intent_id" in context
    # Email should still be in list
    assert len(context["email_list"]) == 1


@pytest.mark.anyio
async def test_voice_delete_confirmed_without_pending_rejected():
    """Server-side gate: confirmed=true without prior pending_confirmation is rejected."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Wichtig", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
        # NO pending_confirmation — LLM tries to skip confirmation
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    # LLM sends confirmed=true without prior request → backend rejects
    result = await executor._tool_delete_email({"email_index": 1, "confirmed": True})
    assert "Keine ausstehende Bestaetigung" in result
    # Email should still be in list (NOT deleted)
    assert len(context["email_list"]) == 1


@pytest.mark.anyio
async def test_voice_send_email_alias_creates_draft():
    """send_email should now behave as a draft-first alias for compose_email."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {}
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 190

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_send_email({
        "to": "x@y.com",
        "subject": "Test",
        "body": "Hi",
    })
    assert "Neuer Entwurf #190 erstellt" in result
    assert context["pending_reply"]["id"] == 190
    assert context["pending_draft_id"] == 190


@pytest.mark.anyio
async def test_voice_reply_creates_draft_not_send():
    """Fix 2 (voice): reply_to_email creates draft, does NOT send."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Test", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_reply_to_email({
        "email_index": 1,
        "reply_text": "Danke fuer die Info",
    })

    # Should create draft, not send
    assert "Entwurf" in result
    assert "absenden" in result.lower()
    assert context.get("pending_reply") is not None
    assert context["pending_reply"]["reply_text"] == "Danke fuer die Info"
    assert "pending_draft_id" in context


@pytest.mark.anyio
async def test_voice_delete_creates_persistent_pending_intent():
    """Voice delete should create a persisted pending intent with ID in context."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Wichtig", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 77
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=5,
        connection_id=9,
    )

    result = await executor._tool_delete_email({"email_index": 1})

    assert "BESTAETIGUNG" in result
    assert context["pending_confirmation"]["id"] == 77
    assert context["pending_intent_id"] == 77
    assert len(added) == 1
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].intent_type == "delete_email"
    assert added[0].conversation_id == 5


@pytest.mark.anyio
async def test_voice_reply_creates_persistent_draft():
    """Voice reply should create a persisted draft with ID in context."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantDraft
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Test", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 88
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=6,
        connection_id=10,
    )

    result = await executor._tool_reply_to_email(
        {"email_index": 1, "reply_text": "Danke fuer die Info"}
    )

    assert "Entwurf #88" in result
    assert context["pending_reply"]["id"] == 88
    assert context["pending_draft_id"] == 88
    assert len(added) == 1
    assert isinstance(added[0], AssistantDraft)
    assert added[0].draft_type == "reply"
    assert added[0].connection_id == 10


@pytest.mark.anyio
async def test_voice_compose_email_creates_persistent_new_draft():
    """Voice compose should create a persisted new-mail draft with pending context."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantDraft
    from app.assistant.voice import VoiceToolExecutor

    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 89
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=6,
        connection_id=10,
    )

    result = await executor._tool_compose_email(
        {"to": "x@y.com", "subject": "Hallo", "body": "Kurzes Update"}
    )

    assert "Neuer Entwurf #89 erstellt" in result
    assert executor.context["pending_reply"]["id"] == 89
    assert executor.context["pending_reply"]["draft_type"] == "new"
    assert executor.context["pending_draft_id"] == 89
    assert isinstance(added[0], AssistantDraft)
    assert added[0].draft_type == "new"


@pytest.mark.anyio
async def test_voice_confirm_and_send_requires_pending_confirmation():
    """confirm_and_send should first ask for explicit confirmation for the current draft."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={"pending_reply": {"id": 89, "draft_type": "new", "sender": "x@y.com"}},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(
        return_value=SimpleNamespace(
            id=89,
            subject="Hallo",
            to_recipients_json={"items": ["x@y.com"]},
        )
    )

    result = await executor._tool_confirm_and_send({})

    assert "BESTAETIGUNG ERFORDERLICH" in result
    assert executor.context["pending_confirmation"]["action"] == "send_draft"
    assert executor.context["pending_confirmation"]["draft_id"] == 89
    assert executor.context["pending_intent_id"] is None


@pytest.mark.anyio
async def test_voice_confirm_and_send_uses_generic_pending_draft():
    """confirm_and_send should send any pending draft after matching confirmation."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={
            "pending_reply": {"id": 89, "draft_type": "new", "sender": "x@y.com"},
            "pending_confirmation": {"action": "send_draft", "draft_id": 89},
        },
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(
        return_value=SimpleNamespace(
            id=89,
            to_recipients_json={"items": ["x@y.com"]},
        )
    )

    with patch(
        "app.assistant.service.AssistantService.send_draft",
        new=AsyncMock(),
    ) as send_mock:
        result = await executor._tool_confirm_and_send({"confirmed": True})

    assert result == "Entwurf gesendet an x@y.com."
    assert executor.context.get("pending_reply") is None
    assert executor.context.get("pending_confirmation") is None
    assert executor.context.get("pending_draft_id") is None
    assert executor.context.get("pending_intent_id") is None
    send_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_confirm_and_send_keeps_pending_draft_on_service_error():
    """Failed send should surface the service error and keep draft context intact."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor
    from app.exceptions import ExternalServiceError

    context = {
        "pending_reply": {"id": 89, "draft_type": "new", "sender": "x@y.com"},
        "pending_confirmation": {"action": "send_draft", "draft_id": 89},
        "pending_draft_id": 89,
    }
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(
        return_value=SimpleNamespace(
            id=89,
            to_recipients_json={"items": ["x@y.com"]},
        )
    )

    with patch(
        "app.assistant.service.AssistantService.send_draft",
        new=AsyncMock(side_effect=ExternalServiceError("Assistant-Provider", "send")),
    ):
        result = await executor._tool_confirm_and_send({"confirmed": True})

    assert "Fehler bei Assistant-Provider: send" == result
    assert executor.context.get("pending_reply") is not None
    assert executor.context.get("pending_confirmation") is not None
    assert executor.context.get("pending_draft_id") == 89


@pytest.mark.anyio
async def test_voice_preview_draft_reads_pending_draft():
    """Voice preview should read the current pending draft from DB/context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {"pending_reply": {"id": 88}}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(
        return_value=SimpleNamespace(
            id=88,
            subject="Re: Test",
            body_text="Danke fuer die Info.",
            to_recipients_json={"items": ["a@b.com"]},
        )
    )

    result = await executor._tool_preview_draft({})

    assert "Entwurf #88." in result
    assert "An: a@b.com" in result
    assert "Betreff: Re: Test" in result


@pytest.mark.anyio
async def test_voice_revise_draft_updates_service_and_context():
    """Voice revise should update the current draft and refresh pending context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {"pending_reply": {"id": 88, "reply_text": "Alt", "subject": "Alt"}}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(
        return_value=SimpleNamespace(id=88, subject="Alt", body_text="Alt")
    )

    updated = SimpleNamespace(id=88, subject="Neu", body_text="Neuer Text")
    with patch(
        "app.assistant.service.AssistantService.update_draft",
        new=AsyncMock(return_value=updated),
    ) as update_mock:
        result = await executor._tool_revise_draft(
            {"subject": "Neu", "body": "Neuer Text"}
        )

    assert "Entwurf #88 aktualisiert." in result
    assert context["pending_reply"]["reply_text"] == "Neuer Text"
    assert context["pending_reply"]["subject"] == "Neu"
    update_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_discard_draft_clears_pending_reply():
    """Voice discard should discard the current draft and clear pending reply context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {"pending_reply": {"id": 88}}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_draft = AsyncMock(return_value=SimpleNamespace(id=88))

    with patch(
        "app.assistant.service.AssistantService.discard_draft",
        new=AsyncMock(),
    ) as discard_mock:
        result = await executor._tool_discard_draft({})

    assert result == "Entwurf #88 wurde verworfen."
    assert context.get("pending_reply") is None
    assert context.get("pending_draft_id") is None
    discard_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_move_intent_captures_original_folder():
    """Move intents should remember the original folder for later undo."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {
                "id": "msg-1",
                "subject": "Test",
                "sender": "a@b.com",
                "snippet": "Hi",
                "parent_folder_id": "folder-inbox",
            },
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 91
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=7,
        connection_id=11,
    )

    result = await executor._tool_move_email({"email_index": 1, "folder": "Archiv"})

    assert "BESTAETIGUNG" in result
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].target_ref_json["original_folder_id"] == "folder-inbox"


@pytest.mark.anyio
async def test_voice_process_message_exposes_pending_ids():
    """Voice response context should expose pending draft and intent IDs."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceService

    conversation = SimpleNamespace(
        id=123,
        context_json={
            "messages": [],
            "email_list": [],
            "current_email_index": 0,
            "current_email_id": None,
            "connection_id": None,
            "pending_reply": {"id": 88},
            "pending_confirmation": {"id": 77},
        },
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()

    svc = VoiceService(mock_db)

    with (
        patch(
            "app.assistant.service.AssistantService.get_or_create_profile",
            new=AsyncMock(
                return_value=SimpleNamespace(llm_provider="ollama", llm_model="qwen")
            ),
        ),
        patch.object(
            svc,
            "_get_or_create_conversation",
            new=AsyncMock(return_value=conversation),
        ),
        patch.object(
            svc,
            "_get_voice_connection",
            new=AsyncMock(return_value=("token", "mailbox@test.de", 9, "microsoft_graph")),
        ),
        patch.object(
            svc,
            "_llm_tool_loop",
            new=AsyncMock(return_value="Fertig"),
        ),
        patch.object(svc, "_log_turn", new=AsyncMock()),
        patch("app.assistant.voice.flag_modified"),
    ):
        result = await svc.process_message("test-tenant", 1, "Hallo", None)

    assert result["context"]["pending_draft_id"] == 88
    assert result["context"]["pending_intent_id"] == 77


def test_resolve_assistant_llm_model_uses_provider_defaults():
    """Assistant model defaults should follow the selected provider."""
    from app.assistant.llm_orchestrator import resolve_assistant_llm_model
    from app.config import settings

    assert resolve_assistant_llm_model("anthropic", None) == settings.llm_model_content
    assert resolve_assistant_llm_model("openai", None) == settings.llm_model_analysis
    assert resolve_assistant_llm_model("ollama", None) == settings.ollama_model
    assert resolve_assistant_llm_model("anthropic", "claude-x") == "claude-x"


def test_assistant_time_utils_return_naive_utc():
    """Assistant DB datetime helpers should return naive UTC timestamps."""
    from app.assistant.time_utils import utc_in_naive, utc_now_naive

    now = utc_now_naive()
    future = utc_in_naive(minutes=15)

    assert now.tzinfo is None
    assert future.tzinfo is None
    assert future > now


@pytest.mark.anyio
async def test_voice_llm_orchestrator_runs_anthropic_tool_loop():
    """Anthropic provider should execute tool_use blocks instead of falling back."""
    import sys
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.llm_orchestrator import VoiceLLMOrchestrator

    class _FakeAsyncAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = SimpleNamespace(create=AsyncMock(side_effect=self._create))
            self.calls = 0

        async def _create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="tool_use",
                            id="tool-1",
                            name="list_emails",
                            input={"limit": 3},
                        )
                    ]
                )
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Hier sind die neuesten Emails.")]
            )

    fake_module = SimpleNamespace(AsyncAnthropic=_FakeAsyncAnthropic)
    executor = SimpleNamespace(execute=AsyncMock(return_value="Tool ok"))
    log_turn = AsyncMock()

    with (
        patch("app.assistant.llm_orchestrator.settings.anthropic_api_key", "test-key"),
        patch.dict(sys.modules, {"anthropic": fake_module}),
    ):
        orchestrator = VoiceLLMOrchestrator(
            llm_provider="anthropic",
            llm_model="claude-sonnet-4-5-20250929",
        )
        result = await orchestrator.run_tool_loop(
            messages=[{"role": "user", "content": "Lies mir Emails vor"}],
            executor=executor,
            context={},
            conversation_id=1,
            tenant_id="test",
            user_id=1,
            log_turn=log_turn,
        )

    assert result == "Hier sind die neuesten Emails."
    executor.execute.assert_awaited_once_with("list_emails", {"limit": 3})
    log_turn.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_summary_uses_anthropic_provider():
    """Email voice summaries should use Anthropic when configured."""
    import sys
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.tool_executor import VoiceToolExecutor

    class _FakeAsyncAnthropic:
        def __init__(self, api_key):
            self.api_key = api_key
            self.messages = SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Kurze Claude-Zusammenfassung.")]
            )))

    fake_module = SimpleNamespace(AsyncAnthropic=_FakeAsyncAnthropic)
    mock_db = AsyncMock()
    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context={},
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-5-20250929",
    )
    executor._fetch_email_text_for_summary = AsyncMock(return_value="Langer Emailtext")

    email = {"id": "msg-1", "subject": "Test", "sender": "user@test.de"}
    with (
        patch("app.assistant.tool_executor.settings.anthropic_api_key", "test-key"),
        patch.dict(sys.modules, {"anthropic": fake_module}),
    ):
        summary = await executor._summarize_email_for_voice(email)

    assert summary == "Kurze Claude-Zusammenfassung."


@pytest.mark.anyio
async def test_service_get_mailbox_policy_reads_cached_status_folders():
    """Mailbox policy should expose cached status folders against live folder list."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.service import AssistantService

    source = SimpleNamespace(
        id=5,
        connection_id=11,
        settings_json={
            "mailbox_policy": {
                "status_folders": {
                    "TODO": {"folder_id": "todo-id", "display_name": "TODO"},
                    "WARTEN": {"folder_id": "wait-id", "display_name": "WARTEN"},
                    "TEMP": {"folder_id": "temp-id", "display_name": "TEMP"},
                    "ARCHIV": {"folder_id": "arch-id", "display_name": "ARCHIV"},
                }
            }
        },
    )
    conn = SimpleNamespace(
        id=11,
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )
    folders = [
        {"id": "inbox", "display_name": "Inbox", "well_known_name": "inbox"},
        {"id": "todo-id", "display_name": "Inbox/todo", "well_known_name": None},
        {"id": "wait-id", "display_name": "Inbox/warten", "well_known_name": None},
        {"id": "temp-id", "display_name": "Inbox/temp", "well_known_name": None},
        {"id": "arch-id", "display_name": "ARCHIV", "well_known_name": None},
    ]

    svc = AssistantService(AsyncMock())
    svc._get_source = AsyncMock(return_value=source)
    svc._get_connection_for_source = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._list_mail_folders = AsyncMock(return_value=folders)

    result = await svc.get_mailbox_policy("test", 1, 5)

    assert result["setup_complete"] is True
    assert result["status_folders"]["INBOX"]["system"] is True
    assert result["status_folders"]["TODO"]["folder_id"] == "todo-id"
    assert result["configured_folder_names"]["INBOX"] == "Inbox"
    assert len(result["available_folders"]) == 5


@pytest.mark.anyio
async def test_service_list_mail_folders_uses_graph_supported_select():
    """Graph mailFolder listing must not request unsupported wellKnownName."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch
    from unittest.mock import call

    from app.assistant.service import AssistantService

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(
        side_effect=[
            {
                "value": [
                    {"id": "inbox", "displayName": "Posteingang"},
                    {"id": "archive-id", "displayName": "Ablage"},
                ]
            },
            {"value": [{"id": "todo-id", "displayName": "todo"}]},
            {"value": []},
            {"value": []},
        ]
    )
    conn = SimpleNamespace(
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )
    svc = AssistantService(AsyncMock())

    with patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=mock_client,
    ):
        result = await svc._list_mail_folders("token", conn)

    assert result == [
        {
            "id": "inbox",
            "display_name": "Posteingang",
            "well_known_name": "inbox",
        },
        {
            "id": "todo-id",
            "display_name": "Posteingang/todo",
            "well_known_name": None,
        },
        {
            "id": "archive-id",
            "display_name": "Ablage",
            "well_known_name": None,
        }
    ]
    mock_client.get.assert_has_awaits(
        [
            call(
                "users/team@test.de/mailFolders",
                params={"$select": "id,displayName", "$top": "100"},
            ),
            call(
                "users/team@test.de/mailFolders/inbox/childFolders",
                params={"$select": "id,displayName", "$top": "100"},
            ),
        ],
        any_order=False,
    )


@pytest.mark.anyio
async def test_service_setup_mailbox_policy_accepts_localized_inbox_root():
    """Configured Posteingang paths should resolve against the internal inbox root."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    source = SimpleNamespace(id=7, connection_id=13, settings_json={})
    conn = SimpleNamespace(
        id=13,
        provider="microsoft_graph",
        mailbox_address="shared@test.de",
        connected_email="shared@test.de",
    )
    mock_db = AsyncMock()
    svc = AssistantService(mock_db)
    svc._get_source = AsyncMock(return_value=source)
    svc._get_connection_for_source = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._list_mail_folders = AsyncMock(
        return_value=[
            {"id": "inbox", "display_name": "Inbox", "well_known_name": "inbox"},
            {"id": "todo-id", "display_name": "Inbox/todo", "well_known_name": None},
            {"id": "wait-id", "display_name": "Inbox/warten", "well_known_name": None},
            {"id": "temp-id", "display_name": "Inbox/temp", "well_known_name": None},
            {"id": "arch-id", "display_name": "Ablage", "well_known_name": None},
        ]
    )

    with patch("app.assistant.service.flag_modified"):
        result = await svc.setup_mailbox_policy(
            "test",
            1,
            7,
            create_missing=False,
            folder_names={
                "INBOX": "Posteingang",
                "TODO": "Posteingang/todo",
                "WARTEN": "Posteingang/warten",
                "TEMP": "Posteingang/temp",
                "ARCHIV": "Ablage",
            },
        )

    assert result["setup_complete"] is True
    assert result["status_folders"]["TODO"]["folder_id"] == "todo-id"
    assert result["configured_folder_names"]["INBOX"] == "Posteingang"
    assert result["configured_folder_names"]["TEMP"] == "Posteingang/temp"


@pytest.mark.anyio
async def test_service_get_mailbox_policy_defaults_to_detected_inbox_root():
    """Unconfigured mailbox policy should default to the localized inbox root."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.service import AssistantService

    source = SimpleNamespace(id=5, connection_id=11, settings_json={})
    conn = SimpleNamespace(
        id=11,
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )
    folders = [
        {"id": "inbox", "display_name": "Posteingang", "well_known_name": "inbox"},
        {
            "id": "todo-id",
            "display_name": "Posteingang/todo",
            "well_known_name": None,
        },
        {
            "id": "wait-id",
            "display_name": "Posteingang/warten",
            "well_known_name": None,
        },
        {
            "id": "temp-id",
            "display_name": "Posteingang/temp",
            "well_known_name": None,
        },
        {"id": "arch-id", "display_name": "Ablage", "well_known_name": None},
    ]

    svc = AssistantService(AsyncMock())
    svc._get_source = AsyncMock(return_value=source)
    svc._get_connection_for_source = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._list_mail_folders = AsyncMock(return_value=folders)

    result = await svc.get_mailbox_policy("test", 1, 5)

    assert result["setup_complete"] is False
    assert result["configured_folder_names"]["INBOX"] == "Posteingang"
    assert result["configured_folder_names"]["TODO"] == "Posteingang/todo"
    assert result["configured_folder_names"]["WARTEN"] == "Posteingang/warten"
    assert result["configured_folder_names"]["TEMP"] == "Posteingang/temp"
    assert result["configured_folder_names"]["ARCHIV"] == "Ablage"


@pytest.mark.anyio
async def test_service_setup_mailbox_policy_creates_missing_folders_and_caches_ids():
    """Setup should create missing status folders and persist the mapping in settings_json."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    source = SimpleNamespace(
        id=7,
        connection_id=13,
        settings_json={},
    )
    conn = SimpleNamespace(
        id=13,
        provider="microsoft_graph",
        mailbox_address="shared@test.de",
        connected_email="shared@test.de",
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc._get_source = AsyncMock(return_value=source)
    svc._get_connection_for_source = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._list_mail_folders = AsyncMock(
        side_effect=[
            [
                {"id": "inbox", "display_name": "Inbox", "well_known_name": "inbox"},
                {
                    "id": "existing-wait",
                    "display_name": "Inbox/warten",
                    "well_known_name": None,
                },
            ],
            [
                {"id": "inbox", "display_name": "Inbox", "well_known_name": "inbox"},
                {"id": "todo-id", "display_name": "Inbox/todo", "well_known_name": None},
                {
                    "id": "existing-wait",
                    "display_name": "Inbox/warten",
                    "well_known_name": None,
                },
                {"id": "temp-id", "display_name": "Inbox/temp", "well_known_name": None},
                {"id": "arch-id", "display_name": "Ablage", "well_known_name": None},
            ],
        ]
    )
    svc._ensure_mail_folder_path = AsyncMock(
        side_effect=[
            {"id": "todo-id", "display_name": "Inbox/todo", "well_known_name": None},
            {"id": "temp-id", "display_name": "Inbox/temp", "well_known_name": None},
            {"id": "arch-id", "display_name": "Ablage", "well_known_name": None},
        ]
    )

    with patch("app.assistant.service.flag_modified") as flag_modified:
        result = await svc.setup_mailbox_policy("test", 1, 7)

    assert result["setup_complete"] is True
    assert result["status_folders"]["WARTEN"]["folder_id"] == "existing-wait"
    assert result["status_folders"]["TODO"]["folder_id"] == "todo-id"
    assert result["configured_folder_names"]["INBOX"] == "Inbox"
    assert source.settings_json["mailbox_policy"]["setup_complete"] is True
    assert source.settings_json["mailbox_policy"]["status_folders"]["ARCHIV"]["folder_id"] == "arch-id"
    assert svc._ensure_mail_folder_path.await_count == 3
    flag_modified.assert_called_once_with(source, "settings_json")


@pytest.mark.anyio
async def test_get_source_mailbox_policy_router_returns_payload():
    """Router should return mailbox policy payload from the service."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant import router as assistant_router

    expected = {
        "source_id": 9,
        "connection_id": 21,
        "mailbox_address": "info@test.de",
        "provider": "microsoft_graph",
        "setup_complete": False,
        "status_folders": {
            "INBOX": {
                "status": "INBOX",
                "folder_id": "inbox",
                "display_name": "Inbox",
                "configured": True,
                "system": True,
            },
            "TODO": {
                "status": "TODO",
                "folder_id": None,
                "display_name": "TODO",
                "configured": False,
                "system": False,
            },
            "WARTEN": {
                "status": "WARTEN",
                "folder_id": None,
                "display_name": "WARTEN",
                "configured": False,
                "system": False,
            },
            "TEMP": {
                "status": "TEMP",
                "folder_id": None,
                "display_name": "TEMP",
                "configured": False,
                "system": False,
            },
            "ARCHIV": {
                "status": "ARCHIV",
                "folder_id": None,
                "display_name": "ARCHIV",
                "configured": False,
                "system": False,
            },
        },
        "configured_folder_names": {
            "INBOX": "Inbox",
            "TODO": "Inbox/todo",
            "WARTEN": "Inbox/warten",
            "TEMP": "Inbox/temp",
            "ARCHIV": "Ablage",
        },
        "available_folders": [],
    }

    with patch(
        "app.assistant.service.AssistantService.get_mailbox_policy",
        new=AsyncMock(return_value=expected),
    ):
        result = await assistant_router.get_source_mailbox_policy(
            9,
            tenant_id="test-tenant",
            user=SimpleNamespace(id=1),
            db=AsyncMock(),
        )

    assert result["source_id"] == 9
    assert result["status_folders"]["INBOX"]["configured"] is True


@pytest.mark.anyio
async def test_service_execute_pending_intent_move_to_status_uses_cached_status_folder():
    """Status moves should resolve the target folder from cached mailbox policy."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    intent = SimpleNamespace(
        id=41,
        tenant_id="test",
        user_id=1,
        conversation_id=7,
        connection_id=12,
        intent_type="move_to_status",
        status="awaiting_confirmation",
        target_ref_json={"email_id": "msg-1", "original_folder_id": "folder-inbox"},
        payload_json={"status": "ARCHIV"},
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_pending_intent = AsyncMock(return_value=intent)
    svc._get_connection_for_intent = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._resolve_status_folder = AsyncMock(return_value=("folder-arch", "ARCHIV"))
    svc._record_undo_log = AsyncMock()
    svc._clear_conversation_pending_intent = AsyncMock()
    svc.resolve_temp_tracking = AsyncMock()

    mock_provider = AsyncMock()
    mock_provider.move_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=AsyncMock(),
    ):
        result = await svc.execute_pending_intent("test", 1, 41)

    assert result is intent
    svc._resolve_status_folder.assert_awaited_once_with(
        tenant_id="test",
        user_id=1,
        connection_id=12,
        status="ARCHIV",
    )
    mock_provider.move_message.assert_awaited_once_with(
        "msg-1", "folder-arch", mailbox="team@test.de"
    )


@pytest.mark.anyio
async def test_service_execute_pending_intent_move_to_status_temp_creates_tracking():
    """TEMP moves should persist expiry tracking after the provider action."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    intent = SimpleNamespace(
        id=52,
        tenant_id="test",
        user_id=1,
        conversation_id=7,
        connection_id=12,
        intent_type="move_to_status",
        status="awaiting_confirmation",
        target_ref_json={
            "email_id": "msg-1",
            "thread_id": "thread-1",
            "subject": "Messeplanung",
            "sender": "kunde@test.de",
            "original_folder_id": "folder-inbox",
            "original_status": "INBOX",
        },
        payload_json={"status": "TEMP", "expires_at": "2026-06-30", "expires_in_days": 30},
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )

    mock_db = AsyncMock()
    svc = AssistantService(mock_db)
    svc.get_pending_intent = AsyncMock(return_value=intent)
    svc._get_connection_for_intent = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._resolve_status_folder = AsyncMock(return_value=("temp-folder", "TEMP"))
    svc._record_undo_log = AsyncMock()
    svc._clear_conversation_pending_intent = AsyncMock()
    svc.upsert_temp_tracking = AsyncMock()
    svc.resolve_temp_tracking = AsyncMock()

    mock_provider = AsyncMock()
    mock_provider.move_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=AsyncMock(),
    ):
        await svc.execute_pending_intent("test", 1, 52)

    svc.upsert_temp_tracking.assert_awaited_once()
    assert svc.upsert_temp_tracking.await_args.kwargs["expires_at"] == "2026-06-30"
    svc.resolve_temp_tracking.assert_not_called()


@pytest.mark.anyio
async def test_service_execute_pending_intent_delete_email_moves_to_deleteditems():
    """Delete intents should move messages into the well-known deleteditems folder."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    intent = SimpleNamespace(
        id=77,
        tenant_id="test",
        user_id=1,
        conversation_id=7,
        connection_id=12,
        intent_type="delete_email",
        status="awaiting_confirmation",
        target_ref_json={
            "email_id": "msg-1",
            "original_folder_id": "folder-inbox",
            "original_folder_name": "Posteingang",
        },
        payload_json={},
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_pending_intent = AsyncMock(return_value=intent)
    svc._get_connection_for_intent = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._record_undo_log = AsyncMock()
    svc._clear_conversation_pending_intent = AsyncMock()

    mock_provider = AsyncMock()
    mock_provider.move_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=AsyncMock(),
    ):
        result = await svc.execute_pending_intent("test", 1, 77)

    assert result is intent
    mock_provider.move_message.assert_awaited_once_with(
        "msg-1",
        "deleteditems",
        mailbox="team@test.de",
    )
    svc._record_undo_log.assert_awaited_once()
    assert svc._record_undo_log.await_args.kwargs["can_undo"] is False
    assert svc._record_undo_log.await_args.kwargs["after_state"] == {
        "folder_name": "Gelöschte Elemente",
        "status": "deleted",
    }


@pytest.mark.anyio
async def test_voice_move_to_status_requires_temp_expiry():
    """TEMP status should be rejected without a concrete expiry date."""
    from unittest.mock import AsyncMock

    from app.assistant.tool_executor import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context={"email_list": [{"id": "msg-1", "subject": "Test", "sender": "a@test.de"}], "current_email_index": 1},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_move_to_status({"email_index": 1, "status": "TEMP"})

    assert "TEMP erfordert" in result


@pytest.mark.anyio
async def test_voice_move_to_status_prefers_current_email_over_default_index_one():
    """Generic follow-up actions should target the currently focused email."""
    from unittest.mock import AsyncMock

    from app.assistant.tool_executor import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Webinar", "sender": "web@test.de"},
            {"id": "msg-2", "subject": "Meeting-Zusammenfassung", "sender": "fireflies@test.de"},
        ],
        "current_email_index": 2,
        "current_email_id": "msg-2",
    }
    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_scoped_connection = AsyncMock(return_value=(12, "token", None))

    result = await executor._tool_move_to_status(
        {"email_index": 1, "status": "TEMP", "expires_in_days": 5}
    )

    assert "Meeting-Zusammenfassung" in result
    assert context["pending_confirmation"]["subject"] == "Meeting-Zusammenfassung"
    assert context["pending_confirmation"]["email_index"] == 2
    assert context["pending_confirmation"]["email_id"] == "msg-2"


@pytest.mark.anyio
async def test_voice_set_temp_expiry_persists_tracking():
    """Setting TEMP expiry should persist tracking and update context."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.tool_executor import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context={
            "email_list": [
                {
                    "id": "msg-1",
                    "subject": "Messestand",
                    "sender": "kunde@test.de",
                    "thread_id": "thread-1",
                    "mailbox": "team@test.de",
                }
            ],
            "current_email_index": 1,
        },
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        connection_id=12,
    )
    executor._get_scoped_connection = AsyncMock(return_value=(12, "token", "team@test.de"))

    service = AsyncMock()
    service.upsert_temp_tracking = AsyncMock()
    with patch("app.assistant.tool_executor.AssistantService", return_value=service):
        result = await executor._tool_set_temp_expiry(
            {"email_index": 1, "expires_in_days": 30}
        )

    assert "Tage" in result or "gesetzt" in result.lower()
    assert executor.context["email_list"][0].get("temp_expires_at") is not None
    service.upsert_temp_tracking.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_review_expired_temp_summarizes_entries():
    """Expired TEMP review should summarize tracked items in voice context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.tool_executor import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    service = AsyncMock()
    service.review_expired_temp = AsyncMock(
        return_value=[
            SimpleNamespace(
                message_external_id="msg-1",
                mailbox_address="team@test.de",
                subject="Messeplanung",
                sender="kunde@test.de",
                expires_at=datetime(2026, 6, 30, 23, 59, 59),
            )
        ]
    )
    with patch("app.assistant.tool_executor.AssistantService", return_value=service):
        result = await executor._tool_review_expired_temp({"limit": 5})

    assert "1 abgelaufene TEMP-Mails" in result
    assert executor.context["temp_review"][0]["message_id"] == "msg-1"


@pytest.mark.anyio
async def test_voice_archive_email_uses_status_move_flow():
    """Archive alias should delegate to move_to_status with ARCHIV."""
    from unittest.mock import AsyncMock

    from app.assistant.tool_executor import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="token",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._tool_move_to_status = AsyncMock(return_value="archiviert")

    result = await executor._tool_archive_email({"email_index": 2})

    assert result == "archiviert"
    executor._tool_move_to_status.assert_awaited_once()
    forwarded = executor._tool_move_to_status.await_args.args[0]
    assert forwarded["status"] == "ARCHIV"
    assert forwarded["email_index"] == 2


@pytest.mark.anyio
async def test_service_undo_discard_draft():
    """Undo should restore a discarded draft back to draft status."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.service import AssistantService

    undo_log = SimpleNamespace(
        id=1,
        can_undo=True,
        undone_at=None,
        action_type="discard_draft",
        draft_id=99,
        status="executed",
    )
    draft = SimpleNamespace(status="discarded", discarded_at="x")

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_undo_log = AsyncMock(return_value=undo_log)
    svc.get_draft = AsyncMock(return_value=draft)

    result = await svc.undo_action("test", 1, 1)

    assert result is undo_log
    assert draft.status == "draft"
    assert draft.discarded_at is None
    assert undo_log.status == "undone"
    assert undo_log.undone_at is not None


@pytest.mark.anyio
async def test_service_undo_mark_read_restores_previous_read_state():
    """Undo should restore the previous read state on the provider."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    undo_log = SimpleNamespace(
        id=2,
        can_undo=True,
        undone_at=None,
        action_type="mark_read",
        connection_id=15,
        target_ref_json={"email_id": "msg-1"},
        before_state_json={"is_read": False},
        status="executed",
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_undo_log = AsyncMock(return_value=undo_log)
    svc._get_connection_for_undo_log = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")

    mock_provider = AsyncMock()
    mock_provider.update_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ):
        result = await svc.undo_action("test", 1, 2)

    assert result is undo_log
    mock_provider.update_message.assert_awaited_once_with(
        "msg-1",
        {"isRead": False},
        mailbox="team@test.de",
    )
    assert undo_log.status == "undone"
    assert undo_log.undone_at is not None


@pytest.mark.anyio
async def test_service_undo_flag_email_restores_previous_flag_state():
    """Undo should restore the previous flag state on the provider."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.service import AssistantService

    undo_log = SimpleNamespace(
        id=3,
        can_undo=True,
        undone_at=None,
        action_type="flag_email",
        connection_id=16,
        target_ref_json={"email_id": "msg-2"},
        before_state_json={"is_flagged": False},
        status="executed",
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )

    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_undo_log = AsyncMock(return_value=undo_log)
    svc._get_connection_for_undo_log = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")

    mock_provider = AsyncMock()
    mock_provider.update_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ):
        result = await svc.undo_action("test", 1, 3)

    assert result is undo_log
    mock_provider.update_message.assert_awaited_once_with(
        "msg-2",
        {"flag": {"flagStatus": "notFlagged"}},
        mailbox="team@test.de",
    )
    assert undo_log.status == "undone"
    assert undo_log.undone_at is not None


@pytest.mark.anyio
async def test_service_undo_last_cleanup_batch_undoes_latest_bulk_moves():
    """Service should undo the newest bulk cleanup batch with undoable move actions."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.assistant.service import AssistantService

    logs = [
        SimpleNamespace(
            id=21,
            pending_intent_id=500,
            can_undo=True,
            undone_at=None,
            metadata_json={"bulk_cleanup": True},
        ),
        SimpleNamespace(
            id=20,
            pending_intent_id=500,
            can_undo=False,
            undone_at=None,
            metadata_json={"bulk_cleanup": True},
        ),
        SimpleNamespace(
            id=10,
            pending_intent_id=400,
            can_undo=True,
            undone_at=None,
            metadata_json={"bulk_cleanup": True},
        ),
    ]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = logs
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    svc = AssistantService(mock_db)
    svc.undo_action = AsyncMock()

    result = await svc.undo_last_cleanup_batch("test", 1)

    assert result == {"pending_intent_id": 500, "undone_count": 1, "total_batch_logs": 2}
    svc.undo_action.assert_awaited_once_with("test", 1, 21)


@pytest.mark.anyio
async def test_service_send_draft_provider_failure_keeps_draft_pending():
    """Provider failure must not mark the draft as sent or clear pending state."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import pytest

    from app.assistant.service import AssistantService
    from app.exceptions import ExternalServiceError

    draft = SimpleNamespace(
        id=15,
        tenant_id="test",
        user_id=1,
        conversation_id=51,
        connection_id=61,
        status="draft",
        subject="Hallo",
        body_html="<p>Hi</p>",
        body_text="Hi",
        to_recipients_json={"items": ["x@y.com"]},
        draft_type="new",
        target_external_id=None,
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_draft = AsyncMock(return_value=draft)
    svc._get_connection_for_draft = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._record_undo_log = AsyncMock()
    svc._clear_conversation_pending_reply = AsyncMock()

    mock_provider = AsyncMock()
    mock_provider.send_mail = AsyncMock(side_effect=RuntimeError("graph down"))

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), pytest.raises(ExternalServiceError):
        await svc.send_draft("test", 1, 15)

    assert draft.status == "draft"
    assert getattr(draft, "sent_at", None) is None
    svc._record_undo_log.assert_not_awaited()
    svc._clear_conversation_pending_reply.assert_not_awaited()


@pytest.mark.anyio
async def test_service_execute_pending_intent_provider_failure_keeps_intent_open():
    """Provider failure must keep the pending intent in awaiting_confirmation."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    import pytest

    from app.assistant.service import AssistantService
    from app.exceptions import ExternalServiceError

    intent = SimpleNamespace(
        id=22,
        tenant_id="test",
        user_id=1,
        conversation_id=52,
        connection_id=62,
        status="awaiting_confirmation",
        intent_type="delete_email",
        target_ref_json={"email_id": "msg-1"},
        payload_json={},
    )
    conn = SimpleNamespace(
        provider="microsoft_graph",
        mailbox_address="team@test.de",
        connected_email="team@test.de",
    )
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock()

    svc = AssistantService(mock_db)
    svc.get_pending_intent = AsyncMock(return_value=intent)
    svc._get_connection_for_intent = AsyncMock(return_value=conn)
    svc._ensure_connection_access_token = AsyncMock(return_value="token")
    svc._record_undo_log = AsyncMock()
    svc._clear_conversation_pending_intent = AsyncMock()

    mock_provider = AsyncMock()
    mock_provider.move_message = AsyncMock(side_effect=RuntimeError("graph down"))

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), pytest.raises(ExternalServiceError):
        await svc.execute_pending_intent("test", 1, 22)

    assert intent.status == "awaiting_confirmation"
    assert getattr(intent, "executed_at", None) is None
    svc._record_undo_log.assert_not_awaited()
    svc._clear_conversation_pending_intent.assert_not_awaited()


@pytest.mark.anyio
async def test_voice_list_attachments():
    """Voice tool should list attachments for the selected email."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Mit Datei", "sender": "a@b.com", "snippet": "Hi"},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {"name": "angebot.pdf", "size": 20480, "contentType": "application/pdf"}
        ]
    }
    executor._get_graph_client = lambda: mock_client

    result = await executor._tool_list_attachments({"email_index": 1})

    assert "angebot.pdf" in result
    assert "application/pdf" in result
    assert context["email_list"][0]["has_attachments"] is True


@pytest.mark.anyio
async def test_voice_list_mailboxes():
    """Voice tool should list connected mailboxes."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            ),
            (
                SimpleNamespace(account_label="Sales", provider="microsoft_graph"),
                "token-2",
                "sales@test.de",
            ),
        ]
    )

    result = await executor._tool_list_mailboxes({})

    assert "Info" in result
    assert "Sales" in result


@pytest.mark.anyio
async def test_voice_count_emails_all_mailboxes():
    """Voice count tool should aggregate counts across mailboxes."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            ),
            (
                SimpleNamespace(account_label="Sales", provider="microsoft_graph"),
                "token-2",
                "sales@test.de",
            ),
        ]
    )

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[{"@odata.count": 4}, {"@odata.count": 7}])

    with patch("app.integrations.microsoft_graph.client.MicrosoftGraphClient", return_value=mock_client):
        result = await executor._tool_count_emails({"all_mailboxes": True, "unread_only": True})

    assert "11 ungelesene Emails" in result
    assert "Info: 4" in result
    assert "Sales: 7" in result


@pytest.mark.anyio
async def test_voice_count_emails_uses_active_folder_scope():
    """Count tool should respect the active folder scope."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={"active_folder_name": "Unwichtig"},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._resolve_folder_id_for_mailbox = AsyncMock(return_value="folder-9")

    mock_client = AsyncMock()
    mock_client.get.return_value = {"@odata.count": 7}

    with patch(
        "app.integrations.microsoft_graph.client.MicrosoftGraphClient",
        return_value=mock_client,
    ):
        result = await executor._tool_count_emails({"unread_only": True})

    assert "7 ungelesene Emails" in result
    assert "im Ordner Unwichtig" in result


@pytest.mark.anyio
async def test_voice_preview_cleanup_builds_operations():
    """Cleanup preview should summarize rule matches across fetched messages."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._load_cleanup_rules = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=1,
                name="LinkedIn unwichtig",
                action_type="move",
                action_payload_json={"target": "Unwichtig"},
                match_criteria_json={
                    "sender_contains": "linkedin.com",
                    "subject_contains": "Suchanfragen gefunden",
                },
            )
        ]
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._fetch_mailbox_messages = AsyncMock(
        return_value=[
            SimpleNamespace(
                provider_message_id="msg-1",
                subject="Sie wurden in 5 Suchanfragen gefunden",
                from_email="jobs@linkedin.com",
                snippet="Profilaufrufe",
                raw={"parentFolderId": "inbox-folder"},
            )
        ]
    )
    executor._resolve_folder_id_for_mailbox = AsyncMock(return_value="folder-unwichtig")

    result = await executor._tool_preview_cleanup({"all_mailboxes": True})

    assert "1 Emails koennten bereinigt werden" in result
    assert executor.context["cleanup_preview"]["operations"][0]["folder"] == "Unwichtig"


@pytest.mark.anyio
async def test_voice_execute_cleanup_requires_confirmation():
    """Cleanup execution should create a persisted pending intent before running."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "cleanup_preview": {
            "operations": [
                {
                    "mailbox": "info@test.de",
                    "email_id": "msg-1",
                    "subject": "Newsletter",
                    "action": "move",
                    "folder": "Unwichtig",
                }
            ]
        }
    }
    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 123
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=11,
        connection_id=15,
    )

    result = await executor._tool_execute_cleanup({})

    assert "BESTAETIGUNG ERFORDERLICH" in result
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].intent_type == "bulk_cleanup"
    assert context["pending_confirmation"]["id"] == 123


@pytest.mark.anyio
async def test_voice_search_emails_populates_context():
    """Voice search should populate email_list context with search results."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._fetch_mailbox_messages = AsyncMock(
        return_value=[
            SimpleNamespace(
                provider_message_id="msg-1",
                subject="Projekt X Status",
                from_email="chef@test.de",
                snippet="Bitte sende ein Update",
                received_at=None,
                is_unread=True,
                raw={"parentFolderId": "inbox", "hasAttachments": False},
            )
        ]
    )

    result = await executor._tool_search_emails({"query": "Projekt X"})

    assert "Projekt X Status" in result
    assert executor.context["email_list"][0]["id"] == "msg-1"
    assert executor.context["current_email_id"] == "msg-1"


@pytest.mark.anyio
async def test_voice_search_emails_filters_by_sender_and_folder():
    """Voice search should support sender and folder scoping."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={"active_folder_name": "Unwichtig"},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._fetch_folder_messages = AsyncMock(
        return_value=[
            SimpleNamespace(
                provider_message_id="msg-1",
                subject="LinkedIn Suchanfragen",
                from_email="jobs@linkedin.com",
                snippet="Sie wurden in 10 Suchanfragen gefunden",
                received_at=None,
                is_unread=True,
                thread_id="thread-1",
                raw={"parentFolderId": "folder-unwichtig", "hasAttachments": False},
            ),
            SimpleNamespace(
                provider_message_id="msg-2",
                subject="Anderer Sender",
                from_email="news@example.com",
                snippet="LinkedIn steht hier nur im Text",
                received_at=None,
                is_unread=True,
                thread_id="thread-2",
                raw={"parentFolderId": "folder-unwichtig", "hasAttachments": False},
            ),
        ]
    )

    result = await executor._tool_search_emails(
        {"query": "LinkedIn", "sender": "linkedin.com"}
    )

    assert "LinkedIn Suchanfragen" in result
    assert "Anderer Sender" not in result
    executor._fetch_folder_messages.assert_awaited_once()
    assert executor.context["email_list"][0]["folder"] == "Unwichtig"


@pytest.mark.anyio
async def test_voice_analyze_mailbox_recommends_cleanup():
    """Mailbox analysis should include cleanup recommendation when operations exist."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._tool_count_emails = AsyncMock(
        return_value="Es gibt 12 ungelesene Emails in dem aktuellen Postfach."
    )
    executor._build_cleanup_preview = AsyncMock(
        return_value={
            "operations": [{"email_id": "msg-1"}],
            "summary": "1 Emails koennten bereinigt werden:",
        }
    )

    result = await executor._tool_analyze_mailbox({})

    assert "12 ungelesene Emails" in result
    assert "Bereinigung empfohlen" in result


@pytest.mark.anyio
async def test_voice_read_thread():
    """Voice thread reader should fetch and summarize thread messages."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {
                "id": "msg-1",
                "subject": "Projekt X",
                "sender": "chef@test.de",
                "snippet": "Status?",
                "thread_id": "thread-123",
            }
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = {
        "value": [
            {
                "subject": "Projekt X",
                "from": {"emailAddress": {"address": "chef@test.de"}},
                "bodyPreview": "Wie ist der Stand?",
            },
            {
                "subject": "Re: Projekt X",
                "from": {"emailAddress": {"address": "ich@test.de"}},
                "bodyPreview": "Ich bin fast fertig.",
            },
        ]
    }
    executor._get_graph_client = lambda: mock_client

    result = await executor._tool_read_thread({"email_index": 1})

    assert "Thread mit 2 Nachrichten" in result
    assert "Zusammenfassung:" in result
    assert "chef@test.de" in result
    assert "ich@test.de" in result
    assert executor.context["current_thread_id"] == "thread-123"
    assert len(executor.context["current_thread"]) == 2


@pytest.mark.anyio
async def test_voice_list_events():
    """Voice tool should list calendar events and store them in context."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._fetch_calendar_events = AsyncMock(
        return_value=[
            SimpleNamespace(
                provider_event_id="evt-1",
                title="Meeting mit Hans",
                starts_at=SimpleNamespace(isoformat=lambda: "2026-03-16T10:00:00+01:00"),
                ends_at=SimpleNamespace(isoformat=lambda: "2026-03-16T10:30:00+01:00"),
                organizer_email="chef@test.de",
                location="Teams",
                raw={
                    "attendees": [
                        {"emailAddress": {"address": "hans@test.de"}},
                        {"emailAddress": {"address": "team@test.de"}},
                    ]
                },
            )
        ]
    )

    result = await executor._tool_list_events({"limit": 5, "mailbox": "info@test.de"})

    assert "Meeting mit Hans" in result
    assert executor.context["calendar_events"][0]["id"] == "evt-1"
    assert executor.context["current_event_id"] == "evt-1"
    assert executor.context["calendar_events"][0]["attendees"] == [
        "hans@test.de",
        "team@test.de",
    ]


@pytest.mark.anyio
async def test_voice_summarize_schedule_uses_existing_events():
    """Calendar overview should summarize the current event context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {
                "id": "evt-1",
                "title": "Meeting mit Hans",
                "starts_at": "2026-03-16T10:00:00+01:00",
                "organizer": "chef@test.de",
                "location": "Teams",
                "mailbox": "info@test.de",
            },
            {
                "id": "evt-2",
                "title": "Projektreview",
                "starts_at": "2026-03-16T14:00:00+01:00",
                "organizer": "pm@test.de",
                "location": "Raum 2",
                "mailbox": "info@test.de",
            },
        ]
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_summarize_schedule({"limit": 2})

    assert result.startswith("Kalender-Ueberblick ueber 2 Termine:")
    assert "Meeting mit Hans" in result
    assert "Projektreview" in result


@pytest.mark.anyio
async def test_voice_summarize_schedule_refreshes_when_requested():
    """Calendar overview should refresh the event list when requested."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {}
    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    async def load_events(_args):
        context["calendar_events"] = [
            {
                "id": "evt-1",
                "title": "Jour fixe",
                "starts_at": "2026-03-16T09:00:00+01:00",
                "organizer": "teamlead@test.de",
                "location": "Teams",
            }
        ]
        return "Liste geladen"

    executor._tool_list_events = AsyncMock(side_effect=load_events)

    result = await executor._tool_summarize_schedule({"refresh": True, "limit": 1})

    assert result.startswith("Kalender-Ueberblick ueber 1 Termine:")
    executor._tool_list_events.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_read_event_uses_calendar_context():
    """Read-event tool should return a speakable event summary with attendees."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {
                "id": "evt-1",
                "title": "Meeting mit Hans",
                "starts_at": "2026-03-16T10:00:00+01:00",
                "ends_at": "2026-03-16T10:30:00+01:00",
                "organizer": "chef@test.de",
                "location": "Teams",
                "attendees": ["hans@test.de", "team@test.de"],
            }
        ]
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_read_event({"event_index": 1})

    assert "Termin 1: Meeting mit Hans." in result
    assert "chef@test.de" in result
    assert "Teams" in result
    assert "hans@test.de, team@test.de" in result
    assert context["current_event_id"] == "evt-1"


@pytest.mark.anyio
async def test_voice_next_event_moves_forward():
    """next_event should move to the next event in the current calendar context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting 1", "starts_at": "2026-03-16T10:00:00+01:00"},
            {"id": "evt-2", "title": "Meeting 2", "starts_at": "2026-03-16T11:00:00+01:00"},
        ],
        "current_event_index": 1,
        "current_event_id": "evt-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_next_event({})

    assert "Termin 2: Meeting 2." in result
    assert context["current_event_index"] == 2
    assert context["current_event_id"] == "evt-2"


@pytest.mark.anyio
async def test_voice_previous_event_moves_back():
    """previous_event should move back in the current calendar context."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting 1", "starts_at": "2026-03-16T10:00:00+01:00"},
            {"id": "evt-2", "title": "Meeting 2", "starts_at": "2026-03-16T11:00:00+01:00"},
        ],
        "current_event_index": 2,
        "current_event_id": "evt-2",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_previous_event({})

    assert "Termin 1: Meeting 1." in result
    assert context["current_event_index"] == 1
    assert context["current_event_id"] == "evt-1"


@pytest.mark.anyio
async def test_voice_mark_read_updates_context():
    """Mark-read tool should patch Graph and update local unread flag."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Test", "sender": "a@b.com", "is_unread": True},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    mock_provider = AsyncMock()
    mock_provider.update_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.assistant.service.AssistantService.record_mail_state_change",
        new=AsyncMock(),
    ) as record_mock:
        result = await executor._tool_mark_read({"email_index": 1})

    assert "als gelesen markiert" in result
    assert context["email_list"][0]["is_unread"] is False
    mock_provider.update_message.assert_awaited_once()
    record_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_flag_email_updates_context():
    """Flag tool should patch Graph and update local flagged state."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Test", "sender": "a@b.com", "is_flagged": False},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    mock_provider = AsyncMock()
    mock_provider.update_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.assistant.service.AssistantService.record_mail_state_change",
        new=AsyncMock(),
    ) as record_mock:
        result = await executor._tool_flag_email({"email_index": 1})

    assert "markiert" in result
    assert context["email_list"][0]["is_flagged"] is True
    mock_provider.update_message.assert_awaited_once()
    record_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_unflag_email_updates_context():
    """Unflag tool should patch Graph and update local flagged state."""
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "email_list": [
            {"id": "msg-1", "subject": "Test", "sender": "a@b.com", "is_flagged": True},
        ],
        "current_email_index": 1,
        "current_email_id": "msg-1",
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    mock_provider = AsyncMock()
    mock_provider.update_message = AsyncMock(return_value={})

    with patch(
        "app.integrations.microsoft_graph.mail_actions.MicrosoftGraphMailActionProvider",
        return_value=mock_provider,
    ), patch(
        "app.assistant.service.AssistantService.record_mail_state_change",
        new=AsyncMock(),
    ) as record_mock:
        result = await executor._tool_unflag_email({"email_index": 1})

    assert "entfernt" in result
    assert context["email_list"][0]["is_flagged"] is False
    mock_provider.update_message.assert_awaited_once()
    record_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_archive_email_reuses_move_flow():
    """Archive tool should delegate to move_email with Archive folder."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._tool_move_email = AsyncMock(return_value="archiviert")

    result = await executor._tool_archive_email({"email_index": 2})

    assert result == "archiviert"
    executor._tool_move_email.assert_awaited_once()
    forwarded = executor._tool_move_email.await_args.args[0]
    assert forwarded["folder"] == "Archive"


@pytest.mark.anyio
async def test_voice_accept_event_requires_confirmation():
    """Accepting an event should create a pending confirmation first."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting mit Hans", "mailbox": "info@test.de"}
        ]
    }
    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 301
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=21,
        connection_id=31,
    )

    result = await executor._tool_accept_event({"event_index": 1})

    assert "BESTAETIGUNG ERFORDERLICH" in result
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].intent_type == "accept_event"
    assert context["pending_confirmation"]["id"] == 301


@pytest.mark.anyio
async def test_voice_decline_event_executes_via_service():
    """Decline event should execute through the central service after confirmation."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting mit Hans", "mailbox": "info@test.de"}
        ],
        "pending_confirmation": {"id": 302, "action": "decline_event"},
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_intent = AsyncMock(
        return_value=SimpleNamespace(id=302, intent_type="decline_event", status="awaiting_confirmation")
    )

    with patch("app.assistant.service.AssistantService.execute_pending_intent", new=AsyncMock()) as exec_mock:
        result = await executor._tool_decline_event({"event_index": 1, "confirmed": True})

    assert "abgelehnt" in result
    exec_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_tentative_event_requires_confirmation():
    """Tentative event response should also go through the confirmation gate."""
    from unittest.mock import AsyncMock

    from app.assistant.models import AssistantPendingIntent
    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting mit Hans", "mailbox": "info@test.de"}
        ]
    }
    added = []
    mock_db = AsyncMock()

    async def add(obj):
        obj.id = 401
        added.append(obj)

    mock_db.add = add
    mock_db.flush = AsyncMock()

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
        conversation_id=21,
        connection_id=31,
    )

    result = await executor._tool_tentative_event({"event_index": 1})

    assert "BESTAETIGUNG ERFORDERLICH" in result
    assert isinstance(added[0], AssistantPendingIntent)
    assert added[0].intent_type == "tentative_event"
    assert context["pending_confirmation"]["id"] == 401


@pytest.mark.anyio
async def test_voice_tentative_event_executes_via_service():
    """Tentative event should execute through the central service after confirmation."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    context = {
        "calendar_events": [
            {"id": "evt-1", "title": "Meeting mit Hans", "mailbox": "info@test.de"}
        ],
        "pending_confirmation": {"id": 402, "action": "tentative_event"},
    }

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._get_pending_intent = AsyncMock(
        return_value=SimpleNamespace(id=402, intent_type="tentative_event", status="awaiting_confirmation")
    )

    with patch("app.assistant.service.AssistantService.execute_pending_intent", new=AsyncMock()) as exec_mock:
        result = await executor._tool_tentative_event({"event_index": 1, "confirmed": True})

    assert "vorlaeufig zugesagt" in result
    exec_mock.assert_awaited_once()


@pytest.mark.anyio
async def test_voice_count_emails_since_last_meeting():
    """Count tool should resolve the last meeting reference before counting."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch

    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )
    executor._list_voice_connections = AsyncMock(
        return_value=[
            (
                SimpleNamespace(account_label="Info", provider="microsoft_graph"),
                "token-1",
                "info@test.de",
            )
        ]
    )
    executor._find_last_meeting_timestamp = AsyncMock(
        return_value="2026-03-14T09:00:00+01:00"
    )

    mock_client = AsyncMock()
    mock_client.get.return_value = {"@odata.count": 3}

    with patch("app.integrations.microsoft_graph.client.MicrosoftGraphClient", return_value=mock_client):
        result = await executor._tool_count_emails(
            {"mailbox": "info@test.de", "since_last_meeting_with": "Hans"}
        )

    assert "3 Emails" in result
    params = mock_client.get.await_args.kwargs["params"]
    assert "receivedDateTime ge 2026-03-14T09:00:00+01:00" in params["$filter"]


@pytest.mark.anyio
async def test_learning_service_combines_undo_patterns():
    """Learning service should include suggestions derived from repeated undo logs."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.assistant.learning import AssistantLearningService

    mock_db = AsyncMock()
    svc = AssistantLearningService(mock_db)
    svc._load_trust_settings = AsyncMock(
        return_value=svc._default_trust_settings()
    )
    svc._find_sender_patterns = AsyncMock(return_value=[])
    svc._find_undo_log_patterns = AsyncMock(
        return_value=[
            {
                "name": "Mails von jobs@linkedin.com nach Unwichtig",
                "match_criteria": {"sender_contains": "jobs@linkedin.com"},
                "action_type": "move",
                "action_payload": {"target": "Unwichtig"},
                "risk_level": "low",
                "confidence": 0.79,
                "priority": 20,
                "reason": "3x gleiche Aktion",
                "source": "undo_log",
                "evidence_count": 3,
            }
        ]
    )
    svc._find_status_patterns = AsyncMock(return_value=[])
    svc._find_category_feedback_patterns = AsyncMock(return_value=[])

    suggestions = await svc.suggest_rules("test", 1)

    assert len(suggestions) == 1
    assert suggestions[0]["action_type"] == "move"
    assert suggestions[0]["action_payload"]["target"] == "Unwichtig"
    assert suggestions[0]["source"] == "undo_log"
    assert suggestions[0]["evidence_count"] == 3
    assert suggestions[0]["autopilot_ready"] is False


@pytest.mark.anyio
async def test_learning_service_deduplicates_and_marks_autopilot_ready():
    """Learning service should prefer the stronger duplicate and expose autopilot metadata."""
    from unittest.mock import AsyncMock

    from app.assistant.learning import AssistantLearningService

    mock_db = AsyncMock()
    svc = AssistantLearningService(mock_db)
    svc._load_trust_settings = AsyncMock(
        return_value=svc._default_trust_settings()
    )
    svc._find_sender_patterns = AsyncMock(
        return_value=[
            {
                "name": "Mails von jobs@linkedin.com nach Unwichtig",
                "match_criteria": {"sender_contains": "jobs@linkedin.com"},
                "action_type": "move",
                "action_payload": {"target": "Unwichtig"},
                "risk_level": "low",
                "confidence": 0.82,
                "priority": 10,
                "reason": "4x Feedback",
                "source": "feedback",
                "evidence_count": 4,
            }
        ]
    )
    svc._find_status_patterns = AsyncMock(return_value=[])
    svc._find_category_feedback_patterns = AsyncMock(return_value=[])
    svc._find_undo_log_patterns = AsyncMock(
        return_value=[
            {
                "name": "Mails von jobs@linkedin.com nach Unwichtig",
                "match_criteria": {"sender_contains": "jobs@linkedin.com"},
                "action_type": "move",
                "action_payload": {"target": "Unwichtig"},
                "risk_level": "low",
                "confidence": 0.91,
                "priority": 20,
                "reason": "5x gleiche Aktion",
                "source": "undo_log",
                "evidence_count": 5,
            }
        ]
    )

    suggestions = await svc.suggest_rules("test", 1)

    assert len(suggestions) == 1
    assert suggestions[0]["confidence"] == 0.91
    assert suggestions[0]["source"] == "undo_log"
    assert suggestions[0]["autopilot_ready"] is True
    assert suggestions[0]["autopilot_blockers"] == []


@pytest.mark.anyio
async def test_learning_service_prefers_status_rule_and_category_payload():
    """Learning service should expose status and category based suggestions."""
    from unittest.mock import AsyncMock

    from app.assistant.learning import AssistantLearningService

    mock_db = AsyncMock()
    svc = AssistantLearningService(mock_db)
    svc._load_trust_settings = AsyncMock(
        return_value=svc._default_trust_settings()
    )
    svc._find_sender_patterns = AsyncMock(return_value=[])
    svc._find_undo_log_patterns = AsyncMock(return_value=[])
    svc._find_status_patterns = AsyncMock(
        return_value=[
            {
                "name": "Mails von kunde@test.de nach WARTEN",
                "match_criteria": {"sender_contains": "kunde@test.de"},
                "action_type": "move_to_status",
                "action_payload": {"status": "WARTEN"},
                "risk_level": "low",
                "confidence": 0.9,
                "priority": 25,
                "reason": "5x nach Status WARTEN verschoben",
                "source": "status_history",
                "evidence_count": 5,
            }
        ]
    )
    svc._find_category_feedback_patterns = AsyncMock(
        return_value=[
            {
                "name": "Mails von kunde@test.de als Projekt: Messe markieren",
                "match_criteria": {"sender_contains": "kunde@test.de"},
                "action_type": "label",
                "action_payload": {"category": "Projekt: Messe"},
                "risk_level": "low",
                "confidence": 0.83,
                "priority": 12,
                "reason": "4x Kategorie Projekt: Messe fuer kunde@test.de",
                "source": "category_feedback",
                "evidence_count": 4,
            }
        ]
    )

    suggestions = await svc.suggest_rules("test", 1)

    assert len(suggestions) == 2
    assert suggestions[0]["action_type"] == "move_to_status"
    assert suggestions[0]["autopilot_ready"] is True
    assert suggestions[1]["action_type"] == "label"
    assert suggestions[1]["action_payload"]["category"] == "Projekt: Messe"


@pytest.mark.anyio
async def test_learning_service_hides_suggestions_below_profile_threshold():
    """Profile suggestion threshold should filter low-confidence candidates."""
    from unittest.mock import AsyncMock

    from app.assistant.learning import AssistantLearningService

    mock_db = AsyncMock()
    svc = AssistantLearningService(mock_db)
    svc._load_trust_settings = AsyncMock(
        return_value={
            "autopilot_min_confidence": 0.9,
            "autopilot_max_rule_risk": "medium",
            "suggestion_min_confidence": 0.8,
        }
    )
    svc._find_sender_patterns = AsyncMock(
        return_value=[
            {
                "name": "Schwacher Vorschlag",
                "match_criteria": {"sender_contains": "lead@test.de"},
                "action_type": "move",
                "action_payload": {"target": "Unwichtig"},
                "risk_level": "low",
                "confidence": 0.75,
                "priority": 10,
                "reason": "zu schwach",
                "source": "feedback",
                "evidence_count": 5,
            }
        ]
    )
    svc._find_undo_log_patterns = AsyncMock(return_value=[])
    svc._find_status_patterns = AsyncMock(return_value=[])
    svc._find_category_feedback_patterns = AsyncMock(return_value=[])

    suggestions = await svc.suggest_rules("test", 1)

    assert suggestions == []


@pytest.mark.anyio
async def test_voice_normalize_since_filter():
    """Voice helper should normalize simple relative date phrases."""
    from app.assistant.voice import VoiceToolExecutor

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context={},
        db=None,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    today = executor._normalize_since_filter("heute")
    friday = executor._normalize_since_filter("freitag frueh")

    assert today is not None
    assert friday is not None
    assert "T00:00:00" in today or "T0" in today
    assert "T06:00:00" in friday or "T06:00" in friday


@pytest.mark.anyio
async def test_graph_client_retries_on_429():
    """MicrosoftGraphClient should retry transient 429 responses."""
    from unittest.mock import AsyncMock, patch

    import httpx

    from app.integrations.microsoft_graph.client import MicrosoftGraphClient

    response_429 = httpx.Response(
        429,
        headers={"Retry-After": "0"},
        request=httpx.Request("GET", "https://graph.microsoft.com/v1.0/me"),
        content=b"throttled",
    )
    response_200 = httpx.Response(
        200,
        request=httpx.Request("GET", "https://graph.microsoft.com/v1.0/me"),
        json={"ok": True},
    )

    request_mock = AsyncMock(side_effect=[response_429, response_200])

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        request = request_mock

    with (
        patch("app.integrations.microsoft_graph.client.httpx.AsyncClient", FakeClient),
        patch("app.integrations.microsoft_graph.client.asyncio.sleep", new=AsyncMock()),
    ):
        client = MicrosoftGraphClient("token", max_retries=1)
        result = await client.get("/me")

    assert result == {"ok": True}
    assert request_mock.await_count == 2


@pytest.mark.anyio
async def test_mailbox_health_summary_builder():
    """Mailbox health summary should reflect cleanup recommendation state."""
    from app.assistant.service import AssistantService

    summary_ok = AssistantService._build_mailbox_health_summary(4, 0, False)
    summary_warn = AssistantService._build_mailbox_health_summary(22, 7, True)

    assert "kein akuter Bereinigungsbedarf" in summary_ok
    assert "voraussichtlich direkt bereinigbar" in summary_warn


@pytest.mark.anyio
async def test_voice_provider_gating():
    """Fix 5 (voice): unsupported provider returns error, not crash."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {"email_list": [], "current_email_index": 0}

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=AsyncMock(),
        tenant_id="test",
        user_id=1,
        provider="google_workspace",  # Not supported
    )

    result = await executor._tool_list_emails({"limit": 5})
    assert "nicht unterstuetzt" in result.lower()
    assert "Microsoft" in result


@pytest.mark.anyio
async def test_voice_create_rule_uses_correct_fields():
    """Fix 4 (voice): create_rule uses sender_contains, not sender_pattern."""
    from unittest.mock import AsyncMock

    from app.assistant.voice import VoiceToolExecutor

    context = {}
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    added = []
    mock_db.add = lambda obj: added.append(obj)

    executor = VoiceToolExecutor(
        access_token="fake",
        mailbox=None,
        context=context,
        db=mock_db,
        tenant_id="test",
        user_id=1,
        provider="microsoft_graph",
    )

    result = await executor._tool_create_rule({
        "name": "Newsletter weg",
        "sender_contains": "newsletter.com",
        "action": "delete",
    })

    assert "Regel" in result
    assert len(added) == 1
    rule = added[0]
    # Must use sender_contains (understood by rule engine), NOT sender_pattern
    assert "sender_contains" in rule.match_criteria_json
    assert "sender_pattern" not in rule.match_criteria_json
