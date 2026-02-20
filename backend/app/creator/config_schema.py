"""Creator module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface


class CreatorInterface(ModuleInterface):
    """Creator module standardized interface."""

    MODULE_NAME = "creator"
    PARAMS = [
        {
            "key": "default_platform",
            "type": "enum",
            "options": ["facebook", "instagram", "linkedin", "twitter"],
            "default": "facebook",
            "description": "Standard-Plattform fuer neue Content-Pieces",
            "affects_kpis": ["pieces_created"],
            "category": "defaults",
        },
        {
            "key": "auto_schedule",
            "type": "boolean",
            "default": False,
            "description": "Genehmigte Pieces automatisch planen",
            "affects_kpis": ["pieces_published"],
            "category": "automation",
        },
        {
            "key": "approval_required",
            "type": "boolean",
            "default": True,
            "description": "Content muss vor Veroeffentlichung genehmigt werden",
            "affects_kpis": ["approval_rate"],
            "category": "workflow",
        },
        {
            "key": "default_content_type",
            "type": "enum",
            "options": ["post", "story", "reel", "article"],
            "default": "post",
            "description": "Standard Content-Typ",
            "affects_kpis": ["pieces_created"],
            "category": "defaults",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return creator health and operational status."""
        from app.config import settings
        from app.creator.models import CreatorPiece

        pending = await db.execute(
            select(func.count(CreatorPiece.id)).where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.status == "draft",
            )
        )
        scheduled = await db.execute(
            select(func.count(CreatorPiece.id)).where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.status == "scheduled",
            )
        )

        return {
            "module": "creator",
            "healthy": True,
            "components": {
                "database": "ok",
                "llm_generator": "ok"
                if settings.anthropic_api_key
                else "not_configured",
                "meta_publisher": "ok"
                if settings.meta_page_access_token
                else "not_configured",
            },
            "drafts_pending": pending.scalar() or 0,
            "scheduled_pending": scheduled.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return creator KPIs."""
        from app.creator.models import CreatorPiece

        cutoff = datetime.utcnow() - timedelta(days=days)

        created = await db.execute(
            select(func.count(CreatorPiece.id)).where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.created_at >= cutoff,
            )
        )
        published = await db.execute(
            select(func.count(CreatorPiece.id)).where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.status == "published",
                CreatorPiece.posted_at >= cutoff,
            )
        )
        pending = await db.execute(
            select(func.count(CreatorPiece.id)).where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.status.in_(["draft", "scheduled"]),
            )
        )

        created_total = created.scalar() or 0
        published_total = published.scalar() or 0

        return {
            "module": "creator",
            "period": f"{days}d",
            "metrics": {
                "pieces_created": created_total,
                "pieces_published": published_total,
                "pieces_pending_approval": pending.scalar() or 0,
                "approval_rate": round(published_total / max(created_total, 1), 2),
            },
        }


creator_interface = CreatorInterface()
