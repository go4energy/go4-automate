"""Contacts module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class ContactsInterface(ModuleInterface):
    """Contacts module standardized interface."""

    MODULE_NAME = "contacts"
    PARAMS = [
        {
            "key": "default_source",
            "type": "string",
            "default": "manual",
            "description": "Standard-Quelle für manuell erstellte Kontakte",
            "category": "general",
        },
        {
            "key": "require_company",
            "type": "boolean",
            "default": False,
            "description": "Kontakte müssen einer Firma zugeordnet sein",
            "category": "validation",
        },
        {
            "key": "auto_extract_domain",
            "type": "boolean",
            "default": True,
            "description": "Domain automatisch aus Website extrahieren",
            "category": "automation",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return Contacts health and operational status."""
        from app.contacts.models import Company, Contact

        total_contacts = await db.execute(
            select(func.count(Contact.id)).where(Contact.tenant_id == tenant_id)
        )
        total_companies = await db.execute(
            select(func.count(Company.id)).where(Company.tenant_id == tenant_id)
        )

        return {
            "module": "contacts",
            "healthy": True,
            "components": {
                "database": "ok",
            },
            "contacts_total": total_contacts.scalar() or 0,
            "companies_total": total_companies.scalar() or 0,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return Contacts KPIs."""
        from app.contacts.models import Company, Contact

        cutoff = datetime.utcnow() - timedelta(days=days)

        total_contacts = await db.execute(
            select(func.count(Contact.id)).where(Contact.tenant_id == tenant_id)
        )
        new_contacts = await db.execute(
            select(func.count(Contact.id)).where(
                Contact.tenant_id == tenant_id,
                Contact.created_at >= cutoff,
            )
        )
        total_companies = await db.execute(
            select(func.count(Company.id)).where(Company.tenant_id == tenant_id)
        )
        new_companies = await db.execute(
            select(func.count(Company.id)).where(
                Company.tenant_id == tenant_id,
                Company.created_at >= cutoff,
            )
        )

        return {
            "module": "contacts",
            "period": f"{days}d",
            "metrics": {
                "contacts_total": total_contacts.scalar() or 0,
                "contacts_new": new_contacts.scalar() or 0,
                "companies_total": total_companies.scalar() or 0,
                "companies_new": new_companies.scalar() or 0,
            },
        }


contacts_interface = ContactsInterface()

# Auto-register for settings discovery
register_module(contacts_interface)
