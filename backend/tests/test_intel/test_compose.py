"""Unit tests for compose helpers — payload validation, tts summary."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.intel.pipeline.compose import _build_tts_summary
from app.intel.schemas import IntelBriefingPayload


def test_tts_summary_empty_event_list():
    s = _build_tts_summary([])
    assert "keine" in s.lower()
    assert len(s) <= 600


def test_tts_summary_truncates_to_600():
    events = [
        {"headline": "Sehr lange Schlagzeile " + "x" * 200}
        for _ in range(20)
    ]
    s = _build_tts_summary(events)
    assert len(s) <= 600


def test_briefing_payload_round_trip():
    now = datetime.utcnow()
    payload = IntelBriefingPayload(
        _schema_version="1.0",
        briefing_type="intel_daily",
        tenant_id="go4energy",
        period={"start": now - timedelta(hours=24), "end": now},
        tts_summary="2 neue Marktbewegungen heute.",
        tts_summary_duration_estimate_sec=3,
        sections=[
            {
                "type": "competitor_change",
                "significance": 0.7,
                "headline": "Wettbewerber X senkt Preise",
                "watch_target": "Konkurrent X",
                "change_type": "price_change",
                "summary": "Preise um 10% gesenkt.",
                "impact_for_us": "Wettbewerbsdruck steigt.",
                "evidence": [{"url": "https://x.com/p", "fetched_at": now}],
            }
        ],
        stats={"sources_checked": 5, "changes_detected": 3, "after_triage": 1},
    )
    dumped = payload.model_dump(by_alias=True, mode="json")
    assert dumped["_schema_version"] == "1.0"
    # Round-trip
    re_validated = IntelBriefingPayload.model_validate(dumped)
    assert re_validated.tenant_id == "go4energy"


def test_briefing_payload_rejects_tts_over_600():
    now = datetime.utcnow()
    with pytest.raises(ValidationError):
        IntelBriefingPayload(
            tenant_id="go4energy",
            period={"start": now, "end": now},
            tts_summary="x" * 601,
        )


def test_briefing_payload_rejects_invalid_section_type():
    now = datetime.utcnow()
    with pytest.raises(ValidationError):
        IntelBriefingPayload(
            tenant_id="go4energy",
            period={"start": now, "end": now},
            tts_summary="ok",
            sections=[
                {
                    "type": "spam",  # invalid
                    "significance": 0.5,
                    "headline": "h",
                    "watch_target": "x",
                    "change_type": "y",
                    "summary": "s",
                    "impact_for_us": "i",
                }
            ],
        )
