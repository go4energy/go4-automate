"""Intel pipeline tasks — run_pipeline_tick + compose-if-due.

Called by ``run_intel_worker.py`` once per interval and by the API
``/intel/admin/run-now`` endpoint for manual triggers.

Concurrency:
- We lock individual sources via ``SELECT ... FOR UPDATE SKIP LOCKED``
  so multiple worker processes can run in parallel without conflict.
- We commit per source so a single failure doesn't lose other work.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.intel.models import IntelBriefing, IntelSource
from app.intel.pipeline import (
    compose_briefing,
    default_period_window,
    detect_change,
    fetch_one,
    reason,
    triage,
)


async def run_pipeline_tick() -> dict:
    """One full tick: pick due sources, process each, then compose briefings.

    Returns a small stats dict for logging/observability.
    """
    stats = {
        "sources_processed": 0,
        "fetches_ok": 0,
        "fetches_failed": 0,
        "events_created": 0,
        "events_triaged": 0,
        "events_reasoned": 0,
        "briefings_composed": 0,
    }

    due_source_ids = await _claim_due_sources()
    for sid in due_source_ids:
        async with async_session() as db:
            try:
                await _process_one_source(db, sid, stats)
                await db.commit()
            except SQLAlchemyError:
                logger.exception("intel tick: db error on source {sid}", sid=sid)
                await db.rollback()
            except Exception:
                logger.exception("intel tick: unhandled error on source {sid}", sid=sid)
                await db.rollback()

    # Once per tick, compose briefings for tenants where the last one is > 24h old
    async with async_session() as db:
        try:
            stats["briefings_composed"] = await _compose_briefings_if_due(db)
            await db.commit()
        except SQLAlchemyError:
            logger.exception("intel tick: db error during briefing compose")
            await db.rollback()

    logger.info("intel tick done: {s}", s=stats)
    return stats


# ── internal ─────────────────────────────────────────────────────────


async def _claim_due_sources() -> list[int]:
    """Return ids of sources that are due for re-fetch.

    Uses FOR UPDATE SKIP LOCKED so concurrent workers don't pick the
    same source. We only read ids here — actual processing happens in
    a fresh session per source so commits are independent.
    """
    now = datetime.utcnow()
    async with async_session() as db:
        stmt = (
            select(IntelSource.id, IntelSource.fetch_interval_sec, IntelSource.last_fetched_at)
            .where(IntelSource.is_active.is_(True))
            .with_for_update(skip_locked=True)
        )
        rows = (await db.execute(stmt)).all()
        await db.commit()

    ids: list[int] = []
    for sid, interval, last in rows:
        if last is None:
            ids.append(sid)
            continue
        if last + timedelta(seconds=interval or 3600) <= now:
            ids.append(sid)
    return ids


async def _process_one_source(
    db: AsyncSession, source_id: int, stats: dict
) -> None:
    """fetch → diff → triage → reason, stopping early on no-change/low-sig."""
    source = await db.get(IntelSource, source_id)
    if source is None or not source.is_active:
        return
    stats["sources_processed"] += 1

    snap = await fetch_one(db, source)
    if snap is None:
        stats["fetches_failed"] += 1
        return
    stats["fetches_ok"] += 1

    event = await detect_change(db, snap)
    if event is None:
        return
    stats["events_created"] += 1

    await triage(db, event)
    stats["events_triaged"] += 1

    if event.processed_at is not None:
        # triage flagged it as below-threshold; skip reason
        return

    await reason(db, event)
    stats["events_reasoned"] += 1


async def _compose_briefings_if_due(db: AsyncSession) -> int:
    """For every tenant with active intel sources, compose a briefing
    when the last one is older than ``intel_briefing_period_hours``.
    Returns the number of briefings written.
    """
    period_start, period_end = default_period_window()

    # Distinct tenants with active sources
    tenants_stmt = (
        select(IntelSource.tenant_id)
        .where(IntelSource.is_active.is_(True))
        .distinct()
    )
    tenants = [row[0] for row in (await db.execute(tenants_stmt)).all()]

    written = 0
    for tenant_id in tenants:
        last_stmt = (
            select(IntelBriefing.created_at)
            .where(IntelBriefing.tenant_id == tenant_id)
            .order_by(IntelBriefing.created_at.desc())
            .limit(1)
        )
        last = (await db.execute(last_stmt)).scalar_one_or_none()
        if last is not None and (
            datetime.utcnow() - last
        ) < timedelta(hours=settings.intel_briefing_period_hours):
            continue
        briefing = await compose_briefing(db, tenant_id, period_start, period_end)
        if briefing is not None:
            written += 1
    return written
