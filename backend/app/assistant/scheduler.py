"""Assistant background worker - periodic intake, classification, and briefing."""

import asyncio

from loguru import logger

from app.assistant.service import AssistantService
from app.database import AsyncSessionLocal


async def run_assistant_cycle(
    tenant_id: str,
    user_id: int,
    max_items: int = 30,
) -> dict:
    """Run one full assistant cycle: intake + classify + rules."""
    async with AsyncSessionLocal() as db:
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
