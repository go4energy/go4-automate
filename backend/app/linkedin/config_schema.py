"""LinkedIn module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class LinkedInInterface(ModuleInterface):
    """LinkedIn module standardized interface."""

    MODULE_NAME = "linkedin"
    PARAMS = [
        {
            "key": "default_daily_limit",
            "type": "integer",
            "default": 100,
            "description": "Standard-Tageslimit pro Account",
            "affects_kpis": ["scrape_rate"],
            "category": "rate_limiting",
        },
        {
            "key": "min_delay_seconds",
            "type": "integer",
            "default": 30,
            "description": "Minimale Verzögerung zwischen Profilen (Sekunden)",
            "affects_kpis": ["detection_risk"],
            "category": "rate_limiting",
        },
        {
            "key": "auto_import_enabled",
            "type": "boolean",
            "default": False,
            "description": "Kontakte automatisch in Funnel importieren",
            "affects_kpis": ["import_rate"],
            "category": "automation",
        },
        {
            "key": "pause_on_rate_limit",
            "type": "boolean",
            "default": True,
            "description": "Jobs pausieren bei Rate-Limit-Erkennung",
            "affects_kpis": ["detection_risk"],
            "category": "safety",
        },
        {
            "key": "session_refresh_hours",
            "type": "integer",
            "default": 24,
            "description": "Session-Refresh-Intervall (Stunden)",
            "category": "session",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return LinkedIn health and operational status."""
        from app.linkedin.models import (
            LinkedInAccount,
            LinkedInContact,
            LinkedInScraperJob,
        )

        accounts = await db.execute(
            select(func.count(LinkedInAccount.id)).where(
                LinkedInAccount.tenant_id == tenant_id,
                LinkedInAccount.status == "active",
            )
        )
        running_jobs = await db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.tenant_id == tenant_id,
                LinkedInScraperJob.status == "running",
            )
        )
        contacts_today = await db.execute(
            select(func.count(LinkedInContact.id)).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.created_at
                >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            )
        )

        return {
            "module": "linkedin",
            "healthy": True,
            "components": {
                "database": "ok",
                "scraper": "standby",  # Will be "running" when worker is active
            },
            "active_accounts": accounts.scalar() or 0,
            "running_jobs": running_jobs.scalar() or 0,
            "contacts_scraped_today": contacts_today.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return LinkedIn KPIs."""
        from app.linkedin.models import (
            LinkedInAccount,
            LinkedInContact,
            LinkedInScraperJob,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total accounts
        accounts = await db.execute(
            select(func.count(LinkedInAccount.id)).where(
                LinkedInAccount.tenant_id == tenant_id
            )
        )

        # Active accounts
        active_accounts = await db.execute(
            select(func.count(LinkedInAccount.id)).where(
                LinkedInAccount.tenant_id == tenant_id,
                LinkedInAccount.status == "active",
            )
        )

        # Jobs completed in period
        jobs_completed = await db.execute(
            select(func.count(LinkedInScraperJob.id)).where(
                LinkedInScraperJob.tenant_id == tenant_id,
                LinkedInScraperJob.status == "completed",
                LinkedInScraperJob.completed_at >= cutoff,
            )
        )

        # Contacts scraped in period
        contacts_scraped = await db.execute(
            select(func.count(LinkedInContact.id)).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.created_at >= cutoff,
            )
        )

        # Contacts imported in period
        contacts_imported = await db.execute(
            select(func.count(LinkedInContact.id)).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.status == "imported",
                LinkedInContact.imported_at >= cutoff,
            )
        )

        # Total profiles scraped all time
        total_profiles = await db.execute(
            select(func.sum(LinkedInAccount.total_profiles_scraped)).where(
                LinkedInAccount.tenant_id == tenant_id
            )
        )

        return {
            "module": "linkedin",
            "period": f"{days}d",
            "metrics": {
                "accounts_total": accounts.scalar() or 0,
                "accounts_active": active_accounts.scalar() or 0,
                "jobs_completed": jobs_completed.scalar() or 0,
                "contacts_scraped": contacts_scraped.scalar() or 0,
                "contacts_imported": contacts_imported.scalar() or 0,
                "total_profiles_all_time": total_profiles.scalar() or 0,
            },
        }


linkedin_interface = LinkedInInterface()

# Auto-register for settings discovery
register_module(linkedin_interface)
