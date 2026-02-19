"""Activity log service."""

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog


class ActivityService:
    """Service for logging and querying activity events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        tenant_id: str,
        module: str,
        action: str,
        title: str,
        detail: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        severity: str = "info",
    ) -> ActivityLog:
        """Create an activity log entry."""
        entry = ActivityLog(
            tenant_id=tenant_id,
            module=module,
            action=action,
            title=title,
            detail=detail,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
        )
        self.db.add(entry)
        await self.db.flush()
        logger.debug(
            "Activity: {module}.{action} - {title}",
            module=module,
            action=action,
            title=title,
        )
        return entry

    async def list_activities(
        self,
        tenant_id: str,
        module: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActivityLog]:
        """List activity logs with optional module filter."""
        stmt = (
            select(ActivityLog)
            .where(ActivityLog.tenant_id == tenant_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if module:
            stmt = stmt.where(ActivityLog.module == module)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_module_stats(self, tenant_id: str, days: int = 7) -> list[dict]:
        """Get aggregated activity stats per module for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                ActivityLog.module,
                ActivityLog.action,
                func.count().label("count"),
            )
            .where(
                ActivityLog.tenant_id == tenant_id,
                ActivityLog.created_at >= since,
            )
            .group_by(ActivityLog.module, ActivityLog.action)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # Group by module
        modules: dict[str, dict] = {}
        for module, action, count in rows:
            if module not in modules:
                modules[module] = {"module": module, "total": 0, "actions": {}}
            modules[module]["actions"][action] = count
            modules[module]["total"] += count

        return list(modules.values())
