"""Assistant background worker - periodic intake, classification, and briefing."""

import asyncio

from loguru import logger
from sqlalchemy import select

from app.assistant.service import AssistantService
from app.database import async_session


async def run_assistant_cycle(
    tenant_id: str,
    user_id: int,
    max_items: int = 30,
) -> dict:
    """Run one full assistant cycle: intake + classify + rules."""
    async with async_session() as db:
        try:
            svc = AssistantService(db)
            result = await svc.run_briefing(tenant_id, user_id, max_items)
            await db.commit()
            logger.info(
                "Assistant cycle: tenant={t} user={u} items={n}",
                t=tenant_id,
                u=user_id,
                n=result["items_processed"],
            )
            return result
        except Exception:
            await db.rollback()
            logger.exception("Assistant cycle failed")
            raise


async def run_worker_loop(
    tenant_id: str,
    user_id: int,
    interval_seconds: int = 300,
    max_iterations: int = 0,
) -> None:
    """Run the assistant worker in a loop.

    Args:
        tenant_id: Tenant to process.
        user_id: User to process.
        interval_seconds: Polling interval (default 5 min).
        max_iterations: Stop after N iterations (0 = unlimited).
    """
    logger.info(
        "Assistant worker starting: tenant={t} user={u} interval={i}s",
        t=tenant_id,
        u=user_id,
        i=interval_seconds,
    )

    iteration = 0
    while True:
        iteration += 1
        try:
            await run_assistant_cycle(tenant_id, user_id)
        except Exception:
            logger.error("Worker iteration {n} failed", n=iteration)

        if max_iterations and iteration >= max_iterations:
            logger.info("Worker reached max iterations ({n})", n=max_iterations)
            break

        await asyncio.sleep(interval_seconds)


# ── Autopilot worker ──────────────────────────────────────────────


async def run_autopilot_for_all_users() -> dict:
    """Discover all users with autopilot_enabled and run a cycle for each.

    Returns aggregate stats across all users.
    """
    from app.assistant.autopilot import AutopilotService
    from app.assistant.autopilot_report import AutopilotReportService
    from app.assistant.models import AssistantProfile

    totals = {"users_processed": 0, "total_executed": 0, "total_queued": 0, "errors": 0}

    async with async_session() as db:
        try:
            result = await db.execute(
                select(AssistantProfile).where(
                    AssistantProfile.autopilot_enabled.is_(True),
                    AssistantProfile.active.is_(True),
                )
            )
            profiles = list(result.scalars().all())
        except Exception:
            logger.exception("Failed to load autopilot profiles")
            return totals

    for profile in profiles:
        async with async_session() as db:
            try:
                svc = AutopilotService(db)
                stats = await svc.run_autopilot_cycle(
                    profile.tenant_id, profile.user_id
                )
                if not stats.get("skipped"):
                    totals["users_processed"] += 1
                    totals["total_executed"] += stats.get("auto_executed", 0)
                    totals["total_queued"] += stats.get("queued_for_review", 0)

                # Generate daily report (idempotent per day)
                report_svc = AutopilotReportService(db)
                await report_svc.generate_daily_report(
                    profile.tenant_id, profile.user_id
                )

                await db.commit()
            except Exception:
                await db.rollback()
                totals["errors"] += 1
                logger.exception(
                    "Autopilot failed: tenant={t} user={u}",
                    t=profile.tenant_id,
                    u=profile.user_id,
                )

    logger.info(
        "Autopilot run complete: users={u} executed={e} queued={q} errors={err}",
        u=totals["users_processed"],
        e=totals["total_executed"],
        q=totals["total_queued"],
        err=totals["errors"],
    )
    return totals


async def run_autopilot_worker_loop(
    interval_seconds: int = 1800,
    max_iterations: int = 0,
) -> None:
    """Run the autopilot worker in a loop.

    Args:
        interval_seconds: Polling interval (default 30 min).
        max_iterations: Stop after N iterations (0 = unlimited).
    """
    logger.info(
        "Autopilot worker starting: interval={i}s",
        i=interval_seconds,
    )

    iteration = 0
    while True:
        iteration += 1
        try:
            await run_autopilot_for_all_users()
        except Exception:
            logger.error("Autopilot iteration {n} failed", n=iteration)

        if max_iterations and iteration >= max_iterations:
            logger.info(
                "Autopilot worker reached max iterations ({n})", n=max_iterations
            )
            break

        await asyncio.sleep(interval_seconds)
