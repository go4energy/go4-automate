"""CRM module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface


class CrmInterface(ModuleInterface):
    """CRM module standardized interface."""

    MODULE_NAME = "crm"
    PARAMS = [
        {
            "key": "auto_followup_enabled",
            "type": "boolean",
            "default": False,
            "description": "Automatische Follow-up Emails senden",
            "affects_kpis": ["conversion_rate"],
            "category": "automation",
        },
        {
            "key": "followup_delay_hours",
            "type": "integer",
            "min": 1,
            "max": 168,
            "default": 24,
            "description": "Wartezeit zwischen Follow-up Schritten (Stunden)",
            "affects_kpis": ["conversion_rate"],
            "category": "scheduling",
        },
        {
            "key": "lead_score_threshold",
            "type": "integer",
            "min": 0,
            "max": 100,
            "default": 50,
            "description": "Ab welchem Score ein Contact als qualifiziert gilt",
            "affects_kpis": ["conversion_rate"],
            "category": "scoring",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return CRM health and operational status."""
        from app.crm.models import CrmContact

        total = await db.execute(
            select(func.count(CrmContact.id)).where(CrmContact.tenant_id == tenant_id)
        )
        active = await db.execute(
            select(func.count(CrmContact.id)).where(
                CrmContact.tenant_id == tenant_id,
                CrmContact.status != "closed",
            )
        )

        return {
            "module": "crm",
            "healthy": True,
            "components": {
                "database": "ok",
            },
            "contacts_total": total.scalar() or 0,
            "contacts_active": active.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return CRM KPIs."""
        from app.crm.models import CrmContact

        cutoff = datetime.utcnow() - timedelta(days=days)

        total = await db.execute(
            select(func.count(CrmContact.id)).where(CrmContact.tenant_id == tenant_id)
        )
        new_contacts = await db.execute(
            select(func.count(CrmContact.id)).where(
                CrmContact.tenant_id == tenant_id,
                CrmContact.created_at >= cutoff,
            )
        )
        avg_score = await db.execute(
            select(func.avg(CrmContact.score)).where(CrmContact.tenant_id == tenant_id)
        )

        return {
            "module": "crm",
            "period": f"{days}d",
            "metrics": {
                "contacts_total": total.scalar() or 0,
                "contacts_new": new_contacts.scalar() or 0,
                "avg_lead_score": round(float(avg_score.scalar() or 0), 1),
            },
        }


crm_interface = CrmInterface()
