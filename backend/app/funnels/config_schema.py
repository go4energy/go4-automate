"""Funnels module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class FunnelsInterface(ModuleInterface):
    """Funnels module standardized interface."""

    MODULE_NAME = "funnels"
    PARAMS = [
        {
            "key": "auto_handoff_enabled",
            "type": "boolean",
            "default": False,
            "description": "Automatische Übergabe an CRM wenn Handoff-Stage erreicht",
            "affects_kpis": ["conversion_rate"],
            "category": "automation",
        },
        {
            "key": "duplicate_check_enabled",
            "type": "boolean",
            "default": True,
            "description": "Duplikate bei Import automatisch prüfen",
            "affects_kpis": ["data_quality"],
            "category": "quality",
        },
        {
            "key": "duplicate_action",
            "type": "select",
            "default": "warn",
            "options": ["warn", "skip", "allow"],
            "description": "Aktion bei erkanntem Duplikat",
            "category": "quality",
        },
        {
            "key": "default_handoff_pipeline_id",
            "type": "integer",
            "default": None,
            "description": "Standard-Pipeline für CRM-Übergabe",
            "category": "handoff",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return Funnels health and operational status."""
        from app.funnels.models import Funnel, FunnelProspect

        funnels = await db.execute(
            select(func.count(Funnel.id)).where(
                Funnel.tenant_id == tenant_id, Funnel.status == "active"
            )
        )
        prospects = await db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.tenant_id == tenant_id
            )
        )
        pending_handoffs = await db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.status == "qualified",
            )
        )

        return {
            "module": "funnels",
            "healthy": True,
            "components": {
                "database": "ok",
            },
            "active_funnels": funnels.scalar() or 0,
            "total_prospects": prospects.scalar() or 0,
            "pending_handoffs": pending_handoffs.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return Funnels KPIs."""
        from app.funnels.models import Funnel, FunnelHandoff, FunnelProspect

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Active funnels
        funnels = await db.execute(
            select(func.count(Funnel.id)).where(
                Funnel.tenant_id == tenant_id, Funnel.status == "active"
            )
        )

        # Total prospects
        prospects = await db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.tenant_id == tenant_id
            )
        )

        # New prospects in period
        new_prospects = await db.execute(
            select(func.count(FunnelProspect.id)).where(
                FunnelProspect.tenant_id == tenant_id,
                FunnelProspect.created_at >= cutoff,
            )
        )

        # Completed handoffs in period
        handoffs = await db.execute(
            select(func.count(FunnelHandoff.id)).where(
                FunnelHandoff.tenant_id == tenant_id,
                FunnelHandoff.status == "completed",
                FunnelHandoff.completed_at >= cutoff,
            )
        )

        # Average prospect score
        avg_score = await db.execute(
            select(func.avg(FunnelProspect.score)).where(
                FunnelProspect.tenant_id == tenant_id
            )
        )

        return {
            "module": "funnels",
            "period": f"{days}d",
            "metrics": {
                "active_funnels": funnels.scalar() or 0,
                "prospects_total": prospects.scalar() or 0,
                "prospects_new": new_prospects.scalar() or 0,
                "handoffs_completed": handoffs.scalar() or 0,
                "avg_prospect_score": round(float(avg_score.scalar() or 0), 1),
            },
        }


funnels_interface = FunnelsInterface()

# Auto-register for settings discovery
register_module(funnels_interface)
