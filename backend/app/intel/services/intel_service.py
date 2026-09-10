"""Intel service — CRUD for WatchTargets, Sources, Briefings, Events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.intel.models import (
    IntelBriefing,
    IntelChangeEvent,
    IntelSource,
    IntelWatchTarget,
)
from app.intel.schemas import (
    SourceCreate,
    SourceUpdate,
    WatchTargetCreate,
    WatchTargetUpdate,
)


class WatchTargetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, include_inactive: bool = False
    ) -> list[IntelWatchTarget]:
        stmt = select(IntelWatchTarget).where(
            IntelWatchTarget.tenant_id == tenant_id
        )
        if not include_inactive:
            stmt = stmt.where(IntelWatchTarget.is_active.is_(True))
        stmt = stmt.order_by(IntelWatchTarget.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, tenant_id: str, target_id: int) -> IntelWatchTarget:
        target = await self.db.get(IntelWatchTarget, target_id)
        if target is None or target.tenant_id != tenant_id:
            raise NotFoundError("WatchTarget", target_id)
        return target

    async def create(
        self, tenant_id: str, data: WatchTargetCreate
    ) -> IntelWatchTarget:
        target = IntelWatchTarget(
            tenant_id=tenant_id,
            name=data.name,
            kind=data.kind,
            context=data.context or {},
            is_active=data.is_active,
        )
        self.db.add(target)
        await self.db.flush()
        await self.db.refresh(target)
        return target

    async def update(
        self, tenant_id: str, target_id: int, data: WatchTargetUpdate
    ) -> IntelWatchTarget:
        target = await self.get(tenant_id, target_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(target, key, value)
        await self.db.flush()
        await self.db.refresh(target)
        return target

    async def delete(self, tenant_id: str, target_id: int) -> None:
        target = await self.get(tenant_id, target_id)
        target.is_active = False
        await self.db.flush()


class SourceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_target(
        self, tenant_id: str, target_id: int
    ) -> list[IntelSource]:
        result = await self.db.execute(
            select(IntelSource)
            .where(
                IntelSource.tenant_id == tenant_id,
                IntelSource.target_id == target_id,
            )
            .order_by(IntelSource.id)
        )
        return list(result.scalars().all())

    async def create(
        self, tenant_id: str, target_id: int, data: SourceCreate
    ) -> IntelSource:
        # Ensure target exists + belongs to tenant
        target = await self.db.get(IntelWatchTarget, target_id)
        if target is None or target.tenant_id != tenant_id:
            raise NotFoundError("WatchTarget", target_id)
        source = IntelSource(
            tenant_id=tenant_id,
            target_id=target_id,
            adapter=data.adapter,
            config=data.config or {},
            fetch_interval_sec=data.fetch_interval_sec,
            is_active=data.is_active,
        )
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def update(
        self, tenant_id: str, source_id: int, data: SourceUpdate
    ) -> IntelSource:
        source = await self.db.get(IntelSource, source_id)
        if source is None or source.tenant_id != tenant_id:
            raise NotFoundError("IntelSource", source_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(source, key, value)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def delete(self, tenant_id: str, source_id: int) -> None:
        source = await self.db.get(IntelSource, source_id)
        if source is None or source.tenant_id != tenant_id:
            raise NotFoundError("IntelSource", source_id)
        await self.db.delete(source)
        await self.db.flush()


class BriefingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, limit: int = 30, offset: int = 0
    ) -> list[IntelBriefing]:
        result = await self.db.execute(
            select(IntelBriefing)
            .where(IntelBriefing.tenant_id == tenant_id)
            .order_by(IntelBriefing.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get(self, tenant_id: str, briefing_id: int) -> IntelBriefing:
        briefing = await self.db.get(IntelBriefing, briefing_id)
        if briefing is None or briefing.tenant_id != tenant_id:
            raise NotFoundError("IntelBriefing", briefing_id)
        return briefing


class EventService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        min_significance: float | None = None,
        change_type: str | None = None,
        target_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IntelChangeEvent]:
        stmt = select(IntelChangeEvent).where(
            IntelChangeEvent.tenant_id == tenant_id
        )
        if min_significance is not None:
            stmt = stmt.where(IntelChangeEvent.significance >= min_significance)
        if change_type:
            stmt = stmt.where(IntelChangeEvent.change_type == change_type)
        if target_id is not None:
            stmt = stmt.join(
                IntelSource, IntelSource.id == IntelChangeEvent.source_id
            ).where(IntelSource.target_id == target_id)
        stmt = (
            stmt.order_by(IntelChangeEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
