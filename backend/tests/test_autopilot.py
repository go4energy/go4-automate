"""Tests for the autopilot service and report."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assistant.autopilot import _RISK_ORDER, AutopilotService
from app.assistant.autopilot_report import AutopilotReportService
from app.integrations.types import MailMessageRef

# ── Helper factories ──────────────────────────────────────────────────


def _make_profile(
    *,
    autopilot_enabled=True,
    autopilot_min_confidence=0.85,
    autopilot_max_rule_risk="medium",
):
    p = MagicMock()
    p.autopilot_enabled = autopilot_enabled
    p.autopilot_min_confidence = autopilot_min_confidence
    p.autopilot_max_rule_risk = autopilot_max_rule_risk
    p.active = True
    p.tenant_id = "t1"
    p.user_id = 1
    return p


def _make_rule(
    *,
    rule_id=1,
    name="Test Rule",
    action_type="move",
    risk_level="low",
    confidence=0.9,
    match_criteria=None,
    enabled=True,
):
    r = MagicMock()
    r.id = rule_id
    r.name = name
    r.action_type = action_type
    r.risk_level = risk_level
    r.confidence = confidence
    r.match_criteria_json = match_criteria or {"sender_contains": "newsletter"}
    r.action_payload_json = {"target": "Archive"}
    r.enabled = enabled
    r.priority = 0
    return r


def _make_message(
    *,
    msg_id="msg-1",
    subject="Newsletter Update",
    from_email="news@newsletter.com",
    snippet="Latest updates",
    is_unread=True,
):
    return MailMessageRef(
        provider_message_id=msg_id,
        subject=subject,
        from_email=from_email,
        received_at=datetime.utcnow(),
        is_unread=is_unread,
        snippet=snippet,
        thread_id="thread-1",
        raw={"parentFolderId": "inbox-folder-id"},
    )


# ── Trust Gate tests ─────────────────────────────────────────────────


class TestTrustGate:
    def setup_method(self):
        self.svc = AutopilotService.__new__(AutopilotService)

    def test_low_risk_always_executes(self):
        rule = _make_rule(risk_level="low")
        for max_risk in ("low", "medium", "high"):
            profile = _make_profile(autopilot_max_rule_risk=max_risk)
            assert self.svc._trust_gate(rule, profile) == "execute"

    def test_medium_risk_executes_if_allowed(self):
        rule = _make_rule(risk_level="medium")
        profile = _make_profile(autopilot_max_rule_risk="medium")
        assert self.svc._trust_gate(rule, profile) == "execute"

        profile_high = _make_profile(autopilot_max_rule_risk="high")
        assert self.svc._trust_gate(rule, profile_high) == "execute"

    def test_medium_risk_skipped_if_profile_only_low(self):
        rule = _make_rule(risk_level="medium")
        profile = _make_profile(autopilot_max_rule_risk="low")
        assert self.svc._trust_gate(rule, profile) == "skip"

    def test_high_risk_always_queued(self):
        rule = _make_rule(risk_level="high")
        for max_risk in ("low", "medium", "high"):
            profile = _make_profile(autopilot_max_rule_risk=max_risk)
            assert self.svc._trust_gate(rule, profile) == "queue"

    def test_delete_always_queued(self):
        rule = _make_rule(action_type="delete", risk_level="low")
        profile = _make_profile(autopilot_max_rule_risk="high")
        assert self.svc._trust_gate(rule, profile) == "queue"


# ── Rule Matching tests ──────────────────────────────────────────────


class TestRuleMatching:
    def setup_method(self):
        self.svc = AutopilotService.__new__(AutopilotService)

    def test_sender_contains_match(self):
        rule = _make_rule(match_criteria={"sender_contains": "newsletter"})
        msg = _make_message(from_email="news@newsletter.com")
        assert self.svc._rule_matches_message(rule, msg, None) is True

    def test_sender_contains_no_match(self):
        rule = _make_rule(match_criteria={"sender_contains": "important"})
        msg = _make_message(from_email="news@newsletter.com")
        assert self.svc._rule_matches_message(rule, msg, None) is False

    def test_subject_contains_match(self):
        rule = _make_rule(match_criteria={"subject_contains": "newsletter"})
        msg = _make_message(subject="Weekly Newsletter")
        assert self.svc._rule_matches_message(rule, msg, None) is True

    def test_subject_regex_match(self):
        rule = _make_rule(match_criteria={"subject_regex": r"^(Re|Fwd):"})
        msg = _make_message(subject="Re: Some thread")
        assert self.svc._rule_matches_message(rule, msg, None) is True

    def test_keywords_match(self):
        rule = _make_rule(match_criteria={"keywords": ["update", "promo"]})
        msg = _make_message(subject="Weekly update", snippet="Check our promo")
        assert self.svc._rule_matches_message(rule, msg, None) is True

    def test_keywords_no_match(self):
        rule = _make_rule(match_criteria={"keywords": ["promo"]})
        msg = _make_message(subject="Important meeting", snippet="Schedule changed")
        assert self.svc._rule_matches_message(rule, msg, None) is False

    def test_empty_criteria_no_match(self):
        rule = MagicMock()
        rule.match_criteria_json = {}
        msg = _make_message()
        assert self.svc._rule_matches_message(rule, msg, None) is False

    def test_none_criteria_no_match(self):
        rule = MagicMock()
        rule.match_criteria_json = None
        msg = _make_message()
        assert self.svc._rule_matches_message(rule, msg, None) is False

    def test_mailbox_scope(self):
        rule = _make_rule(
            match_criteria={"sender_contains": "news", "mailbox": "team@co.com"}
        )
        msg = _make_message(from_email="news@co.com")
        assert self.svc._rule_matches_message(rule, msg, "team@co.com") is True
        assert self.svc._rule_matches_message(rule, msg, "other@co.com") is False

    def test_sender_domain_match(self):
        rule = _make_rule(match_criteria={"sender_domain": "linkedin.com"})
        msg = _make_message(from_email="noreply@linkedin.com")
        assert self.svc._rule_matches_message(rule, msg, None) is True


# ── Confidence filter tests ──────────────────────────────────────────


class TestFindMatchingRule:
    def setup_method(self):
        self.svc = AutopilotService.__new__(AutopilotService)

    def test_rule_above_min_confidence(self):
        rule = _make_rule(confidence=0.9)
        profile = _make_profile(autopilot_min_confidence=0.85)
        msg = _make_message(from_email="news@newsletter.com")
        result = self.svc._find_matching_rule([rule], msg, None, profile)
        assert result is rule

    def test_rule_below_min_confidence_skipped(self):
        rule = _make_rule(confidence=0.5)
        profile = _make_profile(autopilot_min_confidence=0.85)
        msg = _make_message(from_email="news@newsletter.com")
        result = self.svc._find_matching_rule([rule], msg, None, profile)
        assert result is None

    def test_rule_with_no_confidence_passes(self):
        rule = _make_rule(confidence=None)
        profile = _make_profile(autopilot_min_confidence=0.85)
        msg = _make_message(from_email="news@newsletter.com")
        result = self.svc._find_matching_rule([rule], msg, None, profile)
        assert result is rule

    def test_priority_order_respected(self):
        rule_low = _make_rule(
            rule_id=1, confidence=0.9, match_criteria={"sender_contains": "news"}
        )
        rule_high = _make_rule(
            rule_id=2, confidence=0.95, match_criteria={"sender_contains": "news"}
        )
        profile = _make_profile()
        msg = _make_message(from_email="news@co.com")
        # First rule in list wins (already sorted by priority)
        result = self.svc._find_matching_rule([rule_high, rule_low], msg, None, profile)
        assert result is rule_high


# ── Report formatting tests ──────────────────────────────────────────


class TestReportFormatting:
    def setup_method(self):
        self.svc = AutopilotReportService.__new__(AutopilotReportService)

    def test_empty_report(self):
        data = {
            "date": "17.03.2026",
            "total_processed": 0,
            "auto_executed": 0,
            "queued": 0,
            "by_rule": {},
            "by_folder": {},
        }
        text = self.svc._format_report_text(data)
        assert "Keine Emails verarbeitet" in text
        assert "17.03.2026" in text

    def test_report_with_actions(self):
        data = {
            "date": "17.03.2026",
            "total_processed": 15,
            "auto_executed": 12,
            "queued": 3,
            "by_rule": {
                "LinkedIn Archiv": 5,
                "Newsletter Ordner": 4,
            },
            "by_folder": {
                "Archive": 8,
                "Newsletter": 4,
            },
        }
        text = self.svc._format_report_text(data)
        assert "12 Emails verschoben" in text
        assert "3 Emails zur manuellen Pruefung" in text
        assert "LinkedIn Archiv" in text
        assert "5 Treffer" in text

    def test_report_no_queued(self):
        data = {
            "date": "17.03.2026",
            "total_processed": 5,
            "auto_executed": 5,
            "queued": 0,
            "by_rule": {"Rule 1": 5},
            "by_folder": {"Archive": 5},
        }
        text = self.svc._format_report_text(data)
        assert "Keine manuellen Eingriffe erforderlich" in text


# ── Integration tests with mock DB ───────────────────────────────────


@pytest.mark.anyio
async def test_autopilot_cycle_disabled_profile():
    """Cycle should skip if autopilot is disabled."""
    mock_db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = _make_profile(autopilot_enabled=False)
    mock_db.execute.return_value = result_mock

    svc = AutopilotService(mock_db)
    result = await svc.run_autopilot_cycle("t1", 1)
    assert result["skipped"] is True
    assert result["reason"] == "autopilot_disabled"


@pytest.mark.anyio
async def test_autopilot_cycle_no_sources():
    """Cycle should skip if no autopilot sources."""
    mock_db = AsyncMock()
    profile = _make_profile()

    call_count = 0

    async def _mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = profile
        else:
            result.scalars.return_value.all.return_value = []
        return result

    mock_db.execute = AsyncMock(side_effect=_mock_execute)

    svc = AutopilotService(mock_db)
    result = await svc.run_autopilot_cycle("t1", 1)
    assert result["skipped"] is True
    assert result["reason"] == "no_autopilot_sources"


@pytest.mark.anyio
async def test_undo_log_written_on_execute(db_session):
    """Verify undo log is written with autopilot=true metadata."""
    from app.assistant.models import AssistantUndoLog

    svc = AutopilotService(db_session)
    msg = _make_message()

    await svc._write_undo_log(
        "t1",
        1,
        100,
        action_type="move",
        message=msg,
        before_folder_id="inbox-id",
        after_folder_id="archive-id",
        after_folder_name="Archive",
        rule_name="Test Rule",
    )
    await db_session.flush()

    from sqlalchemy import select

    result = await db_session.execute(
        select(AssistantUndoLog).where(AssistantUndoLog.tenant_id == "t1")
    )
    log = result.scalar_one_or_none()
    assert log is not None
    assert log.action_type == "move"
    assert log.metadata_json["autopilot"] is True
    assert log.metadata_json["rule_name"] == "Test Rule"
    assert log.can_undo is True
    assert log.target_ref_json["message_id"] == "msg-1"


# ── Risk order sanity ────────────────────────────────────────────────


class TestRiskOrder:
    def test_low_is_smallest(self):
        assert _RISK_ORDER["low"] < _RISK_ORDER["medium"] < _RISK_ORDER["high"]
