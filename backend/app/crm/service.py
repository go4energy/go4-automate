"""CRM service - CRUD and business logic for contacts."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crm.models import CrmContact
from app.crm.schemas import CrmContactCreate
from app.exceptions import DuplicateError, NotFoundError


class CrmService:
    """Service for contact management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: CrmContactCreate) -> CrmContact:
        """Create a new contact for a tenant."""
        existing = await self.db.execute(
            select(CrmContact).where(
                CrmContact.tenant_id == tenant_id,
                CrmContact.email == data.email,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Contact", "email")

        contact = CrmContact(
            tenant_id=tenant_id,
            email=data.email,
            name=data.name,
            phone=data.phone,
            source=data.source,
            konfigurator_data=data.konfigurator_data,
            notes=data.notes,
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Contact erstellt: {email} (Tenant: {tenant})",
            email=data.email,
            tenant=tenant_id,
        )
        return contact

    async def list_contacts(
        self,
        tenant_id: str,
        status: str | None = None,
        source: str | None = None,
    ) -> list[CrmContact]:
        """List contacts for a tenant with optional filters."""
        query = select(CrmContact).where(CrmContact.tenant_id == tenant_id)
        if status:
            query = query.where(CrmContact.status == status)
        if source:
            query = query.where(CrmContact.source == source)
        query = query.order_by(CrmContact.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, contact_id: int) -> CrmContact:
        """Get a single contact by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(CrmContact).where(
                CrmContact.id == contact_id,
                CrmContact.tenant_id == tenant_id,
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact", contact_id)
        return contact

    async def update_status(
        self, tenant_id: str, contact_id: int, status: str
    ) -> CrmContact:
        """Update contact status."""
        contact = await self.get_by_id(tenant_id, contact_id)
        contact.status = status
        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Contact-Status aktualisiert: {id} -> {status}",
            id=contact_id,
            status=status,
        )
        return contact

    async def toggle_followup_pause(
        self, tenant_id: str, contact_id: int, paused: bool
    ) -> CrmContact:
        """Pause or resume follow-up for a contact."""
        contact = await self.get_by_id(tenant_id, contact_id)
        contact.followup_paused = paused
        await self.db.flush()
        await self.db.refresh(contact)
        action = "pausiert" if paused else "fortgesetzt"
        logger.info(
            "Follow-up {action}: Contact {id}",
            action=action,
            id=contact_id,
        )
        return contact
