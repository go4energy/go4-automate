"""Email Marketing module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class EmailMarketingInterface(ModuleInterface):
    """Email Marketing module standardized interface."""

    MODULE_NAME = "emailmarketing"
    PARAMS = [
        {
            "key": "default_sender_name",
            "type": "string",
            "default": "",
            "description": "Standard-Absendername für neue Provider",
            "category": "general",
        },
        {
            "key": "track_opens",
            "type": "boolean",
            "default": True,
            "description": "Öffnungen automatisch tracken",
            "category": "tracking",
        },
        {
            "key": "track_clicks",
            "type": "boolean",
            "default": True,
            "description": "Klicks automatisch tracken",
            "category": "tracking",
        },
        {
            "key": "auto_unsubscribe_bounces",
            "type": "boolean",
            "default": True,
            "description": "Bounces automatisch abmelden",
            "category": "automation",
        },
        {
            "key": "sequence_send_window",
            "type": "string",
            "default": "09:00-18:00",
            "description": "Standard-Sendefenster für Sequenzen",
            "category": "sequences",
        },
        {
            "key": "sequence_skip_weekends",
            "type": "boolean",
            "default": True,
            "description": "Wochenenden in Sequenzen überspringen",
            "category": "sequences",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return Email Marketing health and operational status."""
        from app.emailmarketing.models import (
            EmailCampaign,
            EmailProvider,
            EmailSequence,
        )

        # Count active providers
        active_providers = await db.execute(
            select(func.count(EmailProvider.id)).where(
                EmailProvider.tenant_id == tenant_id,
                EmailProvider.status == "active",
            )
        )

        # Count campaigns
        total_campaigns = await db.execute(
            select(func.count(EmailCampaign.id)).where(
                EmailCampaign.tenant_id == tenant_id
            )
        )

        # Count active sequences
        active_sequences = await db.execute(
            select(func.count(EmailSequence.id)).where(
                EmailSequence.tenant_id == tenant_id,
                EmailSequence.status == "active",
            )
        )

        provider_count = active_providers.scalar() or 0

        return {
            "module": "emailmarketing",
            "healthy": provider_count > 0,
            "components": {
                "providers": "ok" if provider_count > 0 else "no_provider",
                "database": "ok",
            },
            "active_providers": provider_count,
            "total_campaigns": total_campaigns.scalar() or 0,
            "active_sequences": active_sequences.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return Email Marketing KPIs."""
        from app.emailmarketing.models import (
            EmailCampaign,
            EmailUnsubscribe,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Campaigns sent in period
        campaigns_sent = await db.execute(
            select(func.count(EmailCampaign.id)).where(
                EmailCampaign.tenant_id == tenant_id,
                EmailCampaign.sent_at >= cutoff,
            )
        )

        # Total emails sent
        total_sent = await db.execute(
            select(func.sum(EmailCampaign.sent_count)).where(
                EmailCampaign.tenant_id == tenant_id,
                EmailCampaign.sent_at >= cutoff,
            )
        )

        # Total opens
        total_opened = await db.execute(
            select(func.sum(EmailCampaign.opened_count)).where(
                EmailCampaign.tenant_id == tenant_id,
                EmailCampaign.sent_at >= cutoff,
            )
        )

        # Total clicks
        total_clicked = await db.execute(
            select(func.sum(EmailCampaign.clicked_count)).where(
                EmailCampaign.tenant_id == tenant_id,
                EmailCampaign.sent_at >= cutoff,
            )
        )

        # Unsubscribes
        unsubscribes = await db.execute(
            select(func.count(EmailUnsubscribe.id)).where(
                EmailUnsubscribe.tenant_id == tenant_id,
                EmailUnsubscribe.created_at >= cutoff,
            )
        )

        sent = total_sent.scalar() or 0
        opened = total_opened.scalar() or 0
        clicked = total_clicked.scalar() or 0

        return {
            "module": "emailmarketing",
            "period": f"{days}d",
            "metrics": {
                "campaigns_sent": campaigns_sent.scalar() or 0,
                "emails_sent": sent,
                "emails_opened": opened,
                "emails_clicked": clicked,
                "open_rate": round((opened / sent) * 100, 2) if sent > 0 else 0,
                "click_rate": round((clicked / sent) * 100, 2) if sent > 0 else 0,
                "unsubscribes": unsubscribes.scalar() or 0,
            },
        }


emailmarketing_interface = EmailMarketingInterface()

# Auto-register for settings discovery
register_module(emailmarketing_interface)
