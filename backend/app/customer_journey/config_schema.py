"""Customer Journey module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class CustomerJourneyInterface(ModuleInterface):
    """Customer Journey module standardized interface."""

    MODULE_NAME = "customer_journey"
    PARAMS = [
        {
            "key": "tracking_api_key",
            "type": "string",
            "default": "",
            "description": "API-Key für externe Tracking-Endpunkte (go4.energy, Odoo)",
            "category": "general",
            "secret": True,
        },
        {
            "key": "cookie_max_age_days",
            "type": "integer",
            "default": 180,
            "description": "Lebensdauer des go4_lead Cookies in Tagen",
            "category": "general",
        },
        {
            "key": "notify_on_conversion",
            "type": "boolean",
            "default": True,
            "description": "Benachrichtigung bei Conversion-Events",
            "category": "notifications",
        },
        {
            "key": "notify_on_return_visit",
            "type": "boolean",
            "default": True,
            "description": "Benachrichtigung bei Wiederkehr nach 7+ Tagen",
            "category": "notifications",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return Customer Journey health and operational status."""
        from app.contacts.models import Contact
        from app.customer_journey.models import (
            JourneyCampaign,
            JourneyEvent,
            JourneyRefCode,
        )

        leads_total = await db.execute(
            select(func.count(Contact.id)).where(
                Contact.tenant_id == tenant_id,
                Contact.tracking_hash.isnot(None),
            )
        )
        events_total = await db.execute(
            select(func.count(JourneyEvent.id)).where(
                JourneyEvent.tenant_id == tenant_id,
            )
        )
        refs_total = await db.execute(
            select(func.count(JourneyRefCode.id)).where(
                JourneyRefCode.tenant_id == tenant_id,
            )
        )
        campaigns_total = await db.execute(
            select(func.count(JourneyCampaign.id)).where(
                JourneyCampaign.tenant_id == tenant_id,
            )
        )

        return {
            "module": "customer_journey",
            "healthy": True,
            "components": {"database": "ok", "tracking_api": "ok"},
            "leads_total": leads_total.scalar() or 0,
            "events_total": events_total.scalar() or 0,
            "ref_codes_total": refs_total.scalar() or 0,
            "campaigns_total": campaigns_total.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return Customer Journey KPIs."""
        from app.contacts.models import Contact
        from app.customer_journey.models import JourneyEvent

        cutoff = datetime.utcnow() - timedelta(days=days)

        new_leads = await db.execute(
            select(func.count(Contact.id)).where(
                Contact.tenant_id == tenant_id,
                Contact.tracking_hash.isnot(None),
                Contact.created_at >= cutoff,
            )
        )
        new_events = await db.execute(
            select(func.count(JourneyEvent.id)).where(
                JourneyEvent.tenant_id == tenant_id,
                JourneyEvent.created_at >= cutoff,
            )
        )
        conversions = await db.execute(
            select(func.count(JourneyEvent.id)).where(
                JourneyEvent.tenant_id == tenant_id,
                JourneyEvent.category == "conversion",
                JourneyEvent.created_at >= cutoff,
            )
        )

        return {
            "module": "customer_journey",
            "period": f"{days}d",
            "metrics": {
                "new_leads": new_leads.scalar() or 0,
                "new_events": new_events.scalar() or 0,
                "conversions": conversions.scalar() or 0,
            },
        }


customer_journey_interface = CustomerJourneyInterface()

register_module(customer_journey_interface)
