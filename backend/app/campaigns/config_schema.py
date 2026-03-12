"""Campaigns module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class CampaignsInterface(ModuleInterface):
    """Campaigns module standardized interface."""

    MODULE_NAME = "campaigns"
    PARAMS = [
        {
            "key": "default_daily_budget",
            "type": "number",
            "min": 1.0,
            "max": 10000.0,
            "default": 50.0,
            "description": "Standard-Tagesbudget fuer neue Kampagnen (EUR)",
            "affects_kpis": ["total_spend", "avg_cpl"],
            "category": "budget",
        },
        {
            "key": "auto_optimize",
            "type": "boolean",
            "default": True,
            "description": "Kampagnen-Budgets automatisch optimieren",
            "affects_kpis": ["avg_cpl", "total_spend"],
            "category": "automation",
        },
        {
            "key": "weather_boost_enabled",
            "type": "boolean",
            "default": True,
            "description": "Budget bei gutem Wetter erhoehen",
            "affects_kpis": ["total_spend", "avg_cpl"],
            "category": "automation",
        },
        {
            "key": "max_cpl_threshold",
            "type": "number",
            "min": 0.5,
            "max": 100.0,
            "default": 15.0,
            "description": "Maximaler Cost-per-Lead bevor Kampagne pausiert wird (EUR)",
            "affects_kpis": ["avg_cpl", "campaigns_active"],
            "category": "limits",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return campaigns health and operational status."""
        from app.campaigns.models import CampaignConfig
        from app.config import settings

        active = await db.execute(
            select(func.count(CampaignConfig.id)).where(
                CampaignConfig.tenant_id == tenant_id,
                CampaignConfig.status == "active",
            )
        )

        return {
            "module": "campaigns",
            "healthy": True,
            "components": {
                "database": "ok",
                "meta_ads_api": "ok"
                if settings.meta_system_user_token
                else "not_configured",
                "weather_api": "ok"
                if settings.openweather_api_key
                else "not_configured",
            },
            "campaigns_active": active.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return campaigns KPIs."""
        from app.campaigns.models import CampaignPerformance

        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_date = cutoff.date()

        result = await db.execute(
            select(
                func.coalesce(func.sum(CampaignPerformance.spend), 0),
                func.coalesce(func.sum(CampaignPerformance.impressions), 0),
                func.coalesce(func.sum(CampaignPerformance.clicks), 0),
                func.coalesce(func.sum(CampaignPerformance.leads), 0),
            ).where(
                CampaignPerformance.tenant_id == tenant_id,
                CampaignPerformance.date >= cutoff_date,
            )
        )
        row = result.one()
        spend = float(row[0])
        impressions = int(row[1])
        clicks = int(row[2])
        leads = int(row[3])

        return {
            "module": "campaigns",
            "period": f"{days}d",
            "metrics": {
                "total_spend": round(spend, 2),
                "total_impressions": impressions,
                "total_clicks": clicks,
                "avg_cpl": round(spend / max(leads, 1), 2),
                "avg_ctr": round(clicks / max(impressions, 1), 4),
            },
        }


campaigns_interface = CampaignsInterface()

# Auto-register for settings discovery

register_module(campaigns_interface)
