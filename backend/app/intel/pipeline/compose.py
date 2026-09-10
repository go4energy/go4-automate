"""compose_briefing — aggregate ChangeEvents into a Briefing.

Validates the payload against ``IntelBriefingPayload`` before writing.
A malformed payload raises ``ValidationError`` rather than corrupting
``intel_briefing.payload``.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intel.models import (
    IntelBriefing,
    IntelChangeEvent,
    IntelSource,
    IntelWatchTarget,
)
from app.intel.schemas import IntelBriefingPayload

_TYPE_MAP = {
    "competitor": "competitor_change",
    "regulator": "regulatory_alert",
    "segment": "market_gap_hypothesis",
}


async def compose_briefing(
    db: AsyncSession,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> IntelBriefing | None:
    """Build an IntelBriefing from events in the window.

    Returns the persisted briefing or ``None`` when there are no events
    above the triage threshold (no point writing an empty briefing).
    """
    events = await _load_relevant_events(db, tenant_id, period_start, period_end)
    sources_checked = await _count_sources_checked(
        db, tenant_id, period_start, period_end
    )
    changes_total = await _count_changes(db, tenant_id, period_start, period_end)

    after_triage = len(events)
    if after_triage == 0:
        logger.info(
            "compose_briefing: no qualifying events in window "
            "{start}..{end} for {t}",
            start=period_start,
            end=period_end,
            t=tenant_id,
        )
        return None

    sections = []
    for ev in events:
        section_type = _TYPE_MAP.get(ev["target_kind"], "competitor_change")
        sections.append(
            {
                "type": section_type,
                "significance": float(ev["significance"]),
                "headline": ev["headline"] or "(ohne Titel)",
                "watch_target": ev["target_name"],
                "change_type": ev["change_type"],
                "summary": ev["summary"] or "",
                "impact_for_us": ev["impact_assessment"] or "",
                "suggested_action": None,
                "evidence": ev["evidence"] or [],
                "engagement_event_id": ev["engagement_action_id"],
            }
        )

    tts_summary = _build_tts_summary(events)

    payload_obj = IntelBriefingPayload(
        _schema_version="1.0",
        briefing_type="intel_daily",
        tenant_id=tenant_id,
        period={"start": period_start, "end": period_end},
        tts_summary=tts_summary,
        tts_summary_duration_estimate_sec=max(1, len(tts_summary) // 15),
        sections=sections,
        stats={
            "sources_checked": sources_checked,
            "changes_detected": changes_total,
            "after_triage": after_triage,
        },
    )

    briefing = IntelBriefing(
        tenant_id=tenant_id,
        briefing_uuid=_uuid.uuid4(),
        period_start=period_start,
        period_end=period_end,
        payload=payload_obj.model_dump(by_alias=True, mode="json"),
        tts_summary=tts_summary,
    )
    db.add(briefing)
    await db.flush()
    await db.refresh(briefing)
    logger.info(
        "Intel briefing {bid} composed for {t} ({n} sections)",
        bid=briefing.id,
        t=tenant_id,
        n=after_triage,
    )
    return briefing


# ── helpers ──────────────────────────────────────────────────────────


async def _load_relevant_events(
    db: AsyncSession,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[dict]:
    """Return events with sig >= threshold, joined with target metadata."""
    threshold = settings.intel_triage_threshold
    stmt = (
        select(
            IntelChangeEvent.id,
            IntelChangeEvent.change_type,
            IntelChangeEvent.significance,
            IntelChangeEvent.headline,
            IntelChangeEvent.summary,
            IntelChangeEvent.impact_assessment,
            IntelChangeEvent.evidence,
            IntelChangeEvent.engagement_action_id,
            IntelWatchTarget.name.label("target_name"),
            IntelWatchTarget.kind.label("target_kind"),
        )
        .join(IntelSource, IntelSource.id == IntelChangeEvent.source_id)
        .join(IntelWatchTarget, IntelWatchTarget.id == IntelSource.target_id)
        .where(
            IntelChangeEvent.tenant_id == tenant_id,
            IntelChangeEvent.created_at >= period_start,
            IntelChangeEvent.created_at < period_end,
            IntelChangeEvent.significance >= threshold,
            IntelChangeEvent.headline.isnot(None),
        )
        .order_by(IntelChangeEvent.significance.desc())
    )
    rows = (await db.execute(stmt)).mappings().all()
    return [dict(r) for r in rows]


async def _count_sources_checked(
    db: AsyncSession,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> int:
    stmt = select(func.count(IntelSource.id.distinct())).where(
        IntelSource.tenant_id == tenant_id,
        IntelSource.last_fetched_at >= period_start,
        IntelSource.last_fetched_at < period_end,
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def _count_changes(
    db: AsyncSession,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> int:
    stmt = select(func.count(IntelChangeEvent.id)).where(
        IntelChangeEvent.tenant_id == tenant_id,
        IntelChangeEvent.created_at >= period_start,
        IntelChangeEvent.created_at < period_end,
    )
    return int((await db.execute(stmt)).scalar() or 0)


def _build_tts_summary(events: list[dict]) -> str:
    """≤ 600 chars, full sentences, no exotic acronyms."""
    if not events:
        return "Heute keine relevanten Marktveränderungen erkannt."
    headlines = [e["headline"] for e in events[:5] if e["headline"]]
    intro = f"{len(events)} neue Marktbewegungen heute. "
    body = " ".join(
        h if h.endswith(".") else h + "." for h in headlines
    )
    summary = (intro + body).strip()
    if len(summary) > 600:
        summary = summary[:597].rstrip() + "..."
    return summary


def default_period_window() -> tuple[datetime, datetime]:
    """Default look-back window for the daily briefing."""
    end = datetime.utcnow()
    start = end - timedelta(hours=settings.intel_briefing_period_hours)
    return start, end
