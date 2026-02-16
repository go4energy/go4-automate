"""Lead service - CRUD and business logic for leads."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateError, NotFoundError
from app.models.lead import Lead
from app.schemas.lead import LeadCreate


class LeadService:
    """Service for lead management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: LeadCreate) -> Lead:
        """Create a new lead for a tenant."""
        existing = await self.db.execute(
            select(Lead).where(
                Lead.tenant_id == tenant_id,
                Lead.email == data.email,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Lead", "email")

        lead = Lead(
            tenant_id=tenant_id,
            email=data.email,
            name=data.name,
            phone=data.phone,
            source=data.source,
            konfigurator_data=data.konfigurator_data,
            notes=data.notes,
        )
        self.db.add(lead)
        await self.db.flush()
        await self.db.refresh(lead)
        logger.info(
            "Lead erstellt: {email} (Tenant: {tenant})",
            email=data.email,
            tenant=tenant_id,
        )
        return lead

    async def list_leads(
        self,
        tenant_id: str,
        status: str | None = None,
        source: str | None = None,
    ) -> list[Lead]:
        """List leads for a tenant with optional filters."""
        query = select(Lead).where(Lead.tenant_id == tenant_id)
        if status:
            query = query.where(Lead.status == status)
        if source:
            query = query.where(Lead.source == source)
        query = query.order_by(Lead.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, tenant_id: str, lead_id: int) -> Lead:
        """Get a single lead by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(Lead).where(
                Lead.id == lead_id,
                Lead.tenant_id == tenant_id,
            )
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise NotFoundError("Lead", lead_id)
        return lead

    async def update_status(self, tenant_id: str, lead_id: int, status: str) -> Lead:
        """Update lead status."""
        lead = await self.get_by_id(tenant_id, lead_id)
        lead.status = status
        await self.db.flush()
        await self.db.refresh(lead)
        logger.info(
            "Lead-Status aktualisiert: {id} → {status}",
            id=lead_id,
            status=status,
        )
        return lead

    async def toggle_followup_pause(
        self, tenant_id: str, lead_id: int, paused: bool
    ) -> Lead:
        """Pause or resume follow-up for a lead."""
        lead = await self.get_by_id(tenant_id, lead_id)
        lead.followup_paused = paused
        await self.db.flush()
        await self.db.refresh(lead)
        action = "pausiert" if paused else "fortgesetzt"
        logger.info(
            "Follow-up {action}: Lead {id}",
            action=action,
            id=lead_id,
        )
        return lead
