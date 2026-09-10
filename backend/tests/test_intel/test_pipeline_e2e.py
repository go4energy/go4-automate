"""End-to-end pipeline test: fetch → diff → triage → reason → compose.

External services are stubbed:
- WebAdapter returns canned HTML for two fetches (initial + change)
- AnthropicClient is faked — triage returns classify_change, reason returns JSON
- TEI is unreachable (tested separately) — embedding=None throughout

Verifies the full Worker path: change is detected, classified, reasoned,
and aggregated into an IntelBriefing with a valid IntelBriefingPayload.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.intel.adapters import get_adapter
from app.intel.models import (
    IntelBriefing,
    IntelChangeEvent,
    IntelSnapshot,
    IntelSource,
    IntelWatchTarget,
)
from app.intel.pipeline import (
    compose_briefing,
    detect_change,
    fetch_one,
    reason,
    triage,
)
from app.intel.schemas import FetchResult, IntelBriefingPayload


@pytest_asyncio.fixture
async def tenant_id(client):
    """Ensure tenant exists; return its id."""
    r = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "go4energy", "tenant_name": "go4energy"},
    )
    assert r.status_code in (201, 409)
    return "go4energy"


@pytest_asyncio.fixture
async def source(db_session, tenant_id):
    """A WatchTarget + IntelSource ready for fetching."""
    t = IntelWatchTarget(
        tenant_id=tenant_id,
        name="Konkurrent X",
        kind="competitor",
        context={"industry": "B2B SaaS"},
        is_active=True,
    )
    db_session.add(t)
    await db_session.flush()
    s = IntelSource(
        tenant_id=tenant_id,
        target_id=t.id,
        adapter="web",
        config={"url": "https://x.example/preise"},
        fetch_interval_sec=3600,
        is_active=True,
    )
    db_session.add(s)
    await db_session.flush()
    await db_session.commit()
    return s


# ─── Fakes ───────────────────────────────────────────────────────────


def _fake_fetch_result(text: str, url: str) -> FetchResult:
    return FetchResult(
        text=text,
        parsed={"title": "Pricing", "h1": "Preise"},
        source_url=url,
        fetched_at=datetime.utcnow(),
        raw_size_bytes=len(text.encode("utf-8")),
    )


class _FakeBlock:
    def __init__(self, kind: str, **kw):
        self.type = kind
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeResponse:
    def __init__(self, blocks: list[_FakeBlock]):
        self.content = blocks


class _FakeMessages:
    def __init__(self, responder):
        self._responder = responder

    async def create(self, **kw):
        return self._responder(kw)


class _FakeAnthropic:
    def __init__(self, responder):
        self.messages = _FakeMessages(responder)


def _triage_responder(_kw):
    return _FakeResponse(
        [
            _FakeBlock(
                "tool_use",
                name="classify_change",
                input={"change_type": "price_change", "significance": 0.85},
            )
        ]
    )


def _reason_responder(_kw):
    payload = {
        "headline": "Konkurrent X senkt Preise um 15%",
        "summary": "Die Pricing-Seite zeigt eine deutliche Preissenkung.",
        "impact_assessment": "Wettbewerbsdruck steigt — wir sollten unsere Pricing-Position prüfen.",
        "evidence": [{"url": "https://x.example/preise", "fetched_at": "2026-05-31T10:00:00"}],
    }
    return _FakeResponse([_FakeBlock("text", text=json.dumps(payload))])


# ─── Test ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_full_pipeline_writes_briefing(db_session, tenant_id, source):
    """Two snapshots, triage + reason, briefing aggregation."""

    # ─ 1) First fetch: initial state ─────────────────────────────────
    initial_html_result = _fake_fetch_result(
        "Preise Standard: 49 EUR / Monat. Premium: 149 EUR / Monat.",
        "https://x.example/preise",
    )

    class _AdapterReturningInitial:
        async def fetch(self, *_a, **_kw):
            return initial_html_result

    with patch.object(
        get_adapter("web").__class__, "fetch", _AdapterReturningInitial().fetch
    ):
        snap1 = await fetch_one(db_session, source)
    assert snap1 is not None
    assert snap1.content_hash is not None
    # Embedding is best-effort: present if local Ollama reachable,
    # NULL otherwise. pgvector returns a numpy array; check via len().
    emb = snap1.embedding
    if emb is not None:
        try:
            assert len(emb) == 1024
        except TypeError:
            pass  # scalar/unexpected — ignore in this smoke test
    await db_session.commit()

    # No change against itself — first snapshot returns None from diff
    event0 = await detect_change(db_session, snap1)
    assert event0 is None

    # ─ 2) Second fetch: different content ────────────────────────────
    changed_result = _fake_fetch_result(
        "Preise Standard: 39 EUR / Monat. Premium: 119 EUR / Monat. "
        "Aktion bis 30.6.: kostenloser Onboarding-Workshop.",
        "https://x.example/preise",
    )

    class _AdapterReturningChanged:
        async def fetch(self, *_a, **_kw):
            return changed_result

    with patch.object(
        get_adapter("web").__class__, "fetch", _AdapterReturningChanged().fetch
    ):
        snap2 = await fetch_one(db_session, source)
    assert snap2 is not None
    assert snap2.content_hash != snap1.content_hash
    await db_session.commit()

    # ─ 3) Diff detects change ────────────────────────────────────────
    event = await detect_change(db_session, snap2)
    assert event is not None
    assert event.prev_snapshot_id == snap1.id
    assert event.new_snapshot_id == snap2.id
    assert event.change_type == "unclassified"  # not yet triaged
    assert float(event.significance) == 0.50  # default
    assert event.raw_diff is not None
    assert "text_diff" in event.raw_diff
    await db_session.commit()

    # ─ 4) Triage: fake Haiku tool-use returns price_change/0.85 ─────
    await triage(
        db_session, event, client_factory=lambda: _FakeAnthropic(_triage_responder)
    )
    assert event.change_type == "price_change"
    assert float(event.significance) == pytest.approx(0.85)
    assert event.processed_at is None  # above threshold, ready for reason
    await db_session.commit()

    # ─ 5) Reason: fake Sonnet returns JSON ──────────────────────────
    await reason(
        db_session, event, client_factory=lambda: _FakeAnthropic(_reason_responder)
    )
    assert event.headline.startswith("Konkurrent X senkt Preise")
    assert "Wettbewerbsdruck" in event.impact_assessment
    assert event.evidence is not None
    assert any(
        e.get("url") == "https://x.example/preise" for e in event.evidence
    )
    assert event.processed_at is not None
    await db_session.commit()

    # ─ 6) Compose briefing for the window ───────────────────────────
    period_start = datetime.utcnow() - timedelta(hours=24)
    period_end = datetime.utcnow() + timedelta(minutes=1)
    briefing = await compose_briefing(
        db_session, tenant_id, period_start, period_end
    )
    assert briefing is not None
    assert briefing.tenant_id == tenant_id
    assert briefing.payload is not None

    # Payload validates against the canonical schema
    re = IntelBriefingPayload.model_validate(briefing.payload)
    assert re.tenant_id == tenant_id
    assert len(re.sections) == 1
    sec = re.sections[0]
    assert sec.type == "competitor_change"
    assert sec.change_type == "price_change"
    assert sec.headline.startswith("Konkurrent X senkt Preise")
    assert sec.watch_target == "Konkurrent X"
    assert "Preise" in re.tts_summary or "Konkurrent" in re.tts_summary


@pytest.mark.anyio
async def test_triage_below_threshold_marks_processed(db_session, tenant_id, source):
    """If triage assigns a significance < threshold, processed_at is set
    and the event never reaches reason()."""

    initial = _fake_fetch_result("X", "https://y.example")

    class _Adapter:
        async def fetch(self, *_a, **_kw):
            return initial

    with patch.object(get_adapter("web").__class__, "fetch", _Adapter().fetch):
        snap1 = await fetch_one(db_session, source)

    # Force a change manually so detect_change creates a ChangeEvent
    snap2 = IntelSnapshot(
        tenant_id=tenant_id,
        source_id=source.id,
        fetched_at=datetime.utcnow() + timedelta(seconds=10),
        content_hash="b" * 64,
        text="completely different content here for diff",
        parsed={},
        source_url="https://y.example",
    )
    db_session.add(snap2)
    await db_session.flush()

    event = await detect_change(db_session, snap2)
    assert event is not None

    def low_responder(_kw):
        return _FakeResponse(
            [
                _FakeBlock(
                    "tool_use",
                    name="classify_change",
                    input={"change_type": "content_refresh", "significance": 0.05},
                )
            ]
        )

    await triage(
        db_session, event, client_factory=lambda: _FakeAnthropic(low_responder)
    )
    assert float(event.significance) == pytest.approx(0.05)
    assert event.processed_at is not None  # below threshold

    # Reason should be a no-op (it checks processed_at)
    await reason(
        db_session, event, client_factory=lambda: _FakeAnthropic(_reason_responder)
    )
    assert event.headline is None  # reason did not run
