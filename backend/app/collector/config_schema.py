"""Collector module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface


class CollectorInterface(ModuleInterface):
    """Collector module standardized interface."""

    MODULE_NAME = "collector"
    PARAMS = [
        {
            "key": "default_fetch_interval_hours",
            "type": "integer",
            "min": 1,
            "max": 168,
            "default": 6,
            "description": "Standard-Abrufintervall fuer neue Quellen (Stunden)",
            "affects_kpis": ["findings_per_day", "freshness"],
            "category": "scheduling",
        },
        {
            "key": "auto_categorize",
            "type": "boolean",
            "default": True,
            "description": "Findings automatisch per LLM kategorisieren",
            "affects_kpis": ["categorization_accuracy"],
            "category": "intelligence",
        },
        {
            "key": "change_detection_sensitivity",
            "type": "enum",
            "options": ["low", "medium", "high"],
            "default": "medium",
            "description": "Ab welcher Signifikanz Change-Detection Findings erstellt",
            "affects_kpis": ["change_alerts_per_week"],
            "category": "monitoring",
        },
        {
            "key": "max_findings_per_source",
            "type": "integer",
            "min": 5,
            "max": 100,
            "default": 30,
            "description": "Maximale Findings pro Quelle und Abruf",
            "affects_kpis": ["findings_per_day"],
            "category": "limits",
        },
        {
            "key": "topic_generation_enabled",
            "type": "boolean",
            "default": True,
            "description": "Automatisch Topics aus Findings generieren",
            "affects_kpis": ["topics_generated"],
            "category": "intelligence",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return collector health and operational status."""
        from app.collector.models import CollectorSource
        from app.config import settings

        sources_result = await db.execute(
            select(
                func.count(CollectorSource.id).filter(CollectorSource.active.is_(True)),
                func.count(CollectorSource.id),
            ).where(CollectorSource.tenant_id == tenant_id)
        )
        row = sources_result.one()
        active_sources = row[0]

        # Check due sources
        now = datetime.utcnow()
        due_result = await db.execute(
            select(func.count(CollectorSource.id)).where(
                CollectorSource.tenant_id == tenant_id,
                CollectorSource.active.is_(True),
                CollectorSource.last_fetched_at.is_(None)
                | (
                    CollectorSource.last_fetched_at
                    + func.make_interval(
                        secs=CollectorSource.fetch_interval_hours * 3600
                    )
                    <= now
                ),
            )
        )
        next_due = due_result.scalar() or 0

        return {
            "module": "collector",
            "healthy": True,
            "components": {
                "database": "ok",
                "serper_api": "ok" if settings.serper_api_key else "not_configured",
                "rss_fetcher": "ok",
                "website_scraper": "ok",
                "llm_categorizer": "ok"
                if settings.anthropic_api_key
                else "not_configured",
            },
            "sources_active": active_sources,
            "next_due_sources": next_due,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return collector KPIs."""
        from app.collector.models import (
            CollectorFinding,
            CollectorSource,
            CollectorTopic,
            PageSnapshot,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        findings_count = await db.execute(
            select(func.count(CollectorFinding.id)).where(
                CollectorFinding.tenant_id == tenant_id,
                CollectorFinding.created_at >= cutoff,
            )
        )
        topics_count = await db.execute(
            select(func.count(CollectorTopic.id)).where(
                CollectorTopic.tenant_id == tenant_id,
                CollectorTopic.created_at >= cutoff,
            )
        )
        sources_active = await db.execute(
            select(func.count(CollectorSource.id)).where(
                CollectorSource.tenant_id == tenant_id,
                CollectorSource.active.is_(True),
            )
        )
        changes_count = await db.execute(
            select(func.count(PageSnapshot.id)).where(
                PageSnapshot.tenant_id == tenant_id,
                PageSnapshot.created_at >= cutoff,
                PageSnapshot.change_significance.in_(["high", "medium"]),
            )
        )

        findings_total = findings_count.scalar() or 0
        topics_total = topics_count.scalar() or 0

        return {
            "module": "collector",
            "period": f"{days}d",
            "metrics": {
                "findings_total": findings_total,
                "findings_per_day_avg": round(findings_total / max(days, 1), 1),
                "sources_active": sources_active.scalar() or 0,
                "topics_generated": topics_total,
                "change_detections": changes_count.scalar() or 0,
            },
        }


collector_interface = CollectorInterface()
