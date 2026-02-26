"""Handoff service - transfer prospects to CRM."""

from datetime import datetime
from decimal import Decimal

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Company, Contact
from app.crm.models import CrmDeal, CrmPipeline, CrmPipelineStage
from app.exceptions import NotFoundError, ValidationError
from app.funnels.models import (
    Funnel,
    FunnelActivity,
    FunnelCompany,
    FunnelHandoff,
    FunnelProspect,
)
from app.funnels.schemas import HandoffInitiateRequest


class HandoffService:
    """Service for handling prospect handoffs to CRM."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def initiate_handoff(
        self,
        tenant_id: str,
        prospect_id: int,
        data: HandoffInitiateRequest,
        triggered_by: str = "manual",
        user_id: int | None = None,
    ) -> FunnelHandoff:
        """Initiate a handoff for a prospect."""
        # Get prospect with related data
        result = await self.db.execute(
            select(FunnelProspect)
            .options(
                selectinload(FunnelProspect.company),
                selectinload(FunnelProspect.funnel),
            )
            .where(
                FunnelProspect.id == prospect_id,
                FunnelProspect.tenant_id == tenant_id,
            )
        )
        prospect = result.scalar_one_or_none()
        if not prospect:
            raise NotFoundError("Prospect", prospect_id)

        # Check if already handed off
        if prospect.status == "handed_off":
            raise ValidationError("Prospect wurde bereits übergeben")

        # Check for existing pending handoff
        existing = await self.db.execute(
            select(FunnelHandoff).where(
                FunnelHandoff.prospect_id == prospect_id,
                FunnelHandoff.status.in_(["pending", "processing"]),
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Handoff für diesen Prospect läuft bereits")

        # Create handoff record
        handoff = FunnelHandoff(
            tenant_id=tenant_id,
            funnel_id=prospect.funnel_id,
            prospect_id=prospect_id,
            company_id=prospect.company_id,
            status="pending",
            triggered_by=triggered_by,
            triggered_at=datetime.utcnow(),
            prospect_data=self._create_prospect_snapshot(prospect),
        )
        self.db.add(handoff)
        await self.db.flush()

        # Process handoff
        try:
            await self._process_handoff(handoff, prospect, data, user_id)
            handoff.status = "completed"
            handoff.completed_at = datetime.utcnow()

            # Update prospect status
            prospect.status = "handed_off"

            # Log activity
            activity = FunnelActivity(
                tenant_id=tenant_id,
                prospect_id=prospect_id,
                user_id=user_id,
                activity_type="handoff_completed",
                subject="An CRM übergeben",
                activity_date=datetime.utcnow(),
                metadata_={
                    "handoff_id": handoff.id,
                    "crm_contact_id": handoff.crm_contact_id,
                    "crm_deal_id": handoff.crm_deal_id,
                },
            )
            self.db.add(activity)

        except Exception as e:
            logger.exception("Handoff fehlgeschlagen: {err}", err=str(e))
            handoff.status = "failed"
            handoff.error_message = str(e)
            handoff.retry_count += 1

        await self.db.flush()
        await self.db.refresh(handoff)
        return handoff

    async def _process_handoff(
        self,
        handoff: FunnelHandoff,
        prospect: FunnelProspect,
        data: HandoffInitiateRequest,
        user_id: int | None,
    ) -> None:
        """Process the actual handoff to CRM."""
        funnel = prospect.funnel

        # Check if external CRM is configured
        if funnel.external_crm_config:
            await self._process_external_handoff(handoff, prospect, funnel, data)
        else:
            await self._process_internal_handoff(
                handoff, prospect, funnel, data, user_id
            )

    async def _process_internal_handoff(
        self,
        handoff: FunnelHandoff,
        prospect: FunnelProspect,
        funnel: Funnel,
        data: HandoffInitiateRequest,
        user_id: int | None,
    ) -> None:
        """Process handoff to internal CRM."""
        tenant_id = prospect.tenant_id

        # Create or find company in CRM
        crm_company_id = None
        if prospect.company:
            crm_company = await self._find_or_create_crm_company(
                tenant_id, prospect.company, user_id
            )
            crm_company_id = crm_company.id
            handoff.crm_company_id = crm_company_id

            # Update funnel company reference
            prospect.company.crm_company_id = crm_company_id

        # Create contact in CRM
        crm_contact = await self._create_crm_contact(
            tenant_id, prospect, crm_company_id, user_id
        )
        handoff.crm_contact_id = crm_contact.id
        prospect.crm_contact_id = crm_contact.id

        # Create deal if requested
        if data.create_deal:
            crm_deal = await self._create_crm_deal(
                tenant_id, funnel, prospect, crm_contact.id, crm_company_id, data, user_id
            )
            handoff.crm_deal_id = crm_deal.id
            prospect.crm_deal_id = crm_deal.id

        logger.info(
            "Internes Handoff abgeschlossen: Prospect {id} -> Contact {cid}",
            id=prospect.id,
            cid=crm_contact.id,
        )

    async def _find_or_create_crm_company(
        self, tenant_id: str, funnel_company: FunnelCompany, owner_id: int | None
    ) -> Company:
        """Find or create a company in the CRM."""
        # Try to find by domain
        if funnel_company.domain:
            result = await self.db.execute(
                select(Company).where(
                    Company.tenant_id == tenant_id,
                    Company.domain == funnel_company.domain,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Create new company
        crm_company = Company(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=funnel_company.name,
            domain=funnel_company.domain,
            website=funnel_company.website,
            industry=funnel_company.industry,
            size=funnel_company.size,
            address=funnel_company.address,
            phone=funnel_company.phone,
            email=funnel_company.email,
            tags=funnel_company.tags,
            custom_fields=funnel_company.custom_fields,
        )
        self.db.add(crm_company)
        await self.db.flush()
        logger.info("CRM Company erstellt: {name}", name=crm_company.name)
        return crm_company

    async def _create_crm_contact(
        self,
        tenant_id: str,
        prospect: FunnelProspect,
        company_id: int | None,
        owner_id: int | None,
    ) -> Contact:
        """Create a contact in the CRM."""
        # Check for existing contact by email
        if prospect.email:
            result = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == prospect.email,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                # Update existing contact with new info
                existing.company_id = company_id or existing.company_id
                existing.phone = prospect.phone or existing.phone
                existing.mobile = prospect.mobile or existing.mobile
                existing.position = prospect.position or existing.position
                existing.linkedin = prospect.linkedin_url or existing.linkedin
                existing.twitter = prospect.twitter_url or existing.twitter
                await self.db.flush()
                return existing

        # Create new contact
        crm_contact = Contact(
            tenant_id=tenant_id,
            company_id=company_id,
            owner_id=owner_id,
            email=prospect.email or f"noemail_{prospect.id}@placeholder.local",
            name=prospect.name,
            phone=prospect.phone,
            mobile=prospect.mobile,
            position=prospect.position,
            source=f"funnel:{prospect.funnel_id}",
            tags=prospect.tags,
            custom_fields={
                **prospect.custom_fields,
                "funnel_source": prospect.source,
                "funnel_score": prospect.score,
            },
            linkedin=prospect.linkedin_url,
            twitter=prospect.twitter_url,
        )
        self.db.add(crm_contact)
        await self.db.flush()
        logger.info("CRM Contact erstellt: {name}", name=crm_contact.name)
        return crm_contact

    async def _create_crm_deal(
        self,
        tenant_id: str,
        funnel: Funnel,
        prospect: FunnelProspect,
        contact_id: int,
        company_id: int | None,
        data: HandoffInitiateRequest,
        owner_id: int | None,
    ) -> CrmDeal:
        """Create a deal in the CRM."""
        # Get pipeline and stage
        pipeline_id = funnel.handoff_pipeline_id
        stage_id = funnel.handoff_stage_id

        # If not configured, get default pipeline
        if not pipeline_id:
            result = await self.db.execute(
                select(CrmPipeline).where(
                    CrmPipeline.tenant_id == tenant_id,
                    CrmPipeline.is_default == True,
                )
            )
            pipeline = result.scalar_one_or_none()
            if not pipeline:
                raise ValidationError("Keine Pipeline für Handoff konfiguriert")
            pipeline_id = pipeline.id

            # Get first stage
            stage_result = await self.db.execute(
                select(CrmPipelineStage)
                .where(CrmPipelineStage.pipeline_id == pipeline_id)
                .order_by(CrmPipelineStage.position)
                .limit(1)
            )
            first_stage = stage_result.scalar_one_or_none()
            if first_stage:
                stage_id = first_stage.id

        if not stage_id:
            raise ValidationError("Keine Stage für Handoff konfiguriert")

        # Get stage probability
        stage_result = await self.db.execute(
            select(CrmPipelineStage).where(CrmPipelineStage.id == stage_id)
        )
        stage = stage_result.scalar_one_or_none()
        probability = stage.probability if stage else 0

        # Create deal
        title = data.deal_title or f"Deal: {prospect.name}"
        value = Decimal(str(data.deal_value)) if data.deal_value else None

        crm_deal = CrmDeal(
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            stage_id=stage_id,
            contact_id=contact_id,
            company_id=company_id,
            owner_id=owner_id,
            title=title,
            value=value,
            currency="EUR",
            probability=probability,
            status="open",
            priority="medium",
            tags=prospect.tags,
            description=data.notes or f"Automatisch erstellt aus Funnel: {funnel.name}",
            custom_fields={
                "funnel_id": funnel.id,
                "funnel_name": funnel.name,
                "prospect_score": prospect.score,
            },
        )
        self.db.add(crm_deal)
        await self.db.flush()
        logger.info("CRM Deal erstellt: {title}", title=crm_deal.title)
        return crm_deal

    async def _process_external_handoff(
        self,
        handoff: FunnelHandoff,
        prospect: FunnelProspect,
        funnel: Funnel,
        data: HandoffInitiateRequest,
    ) -> None:
        """Process handoff to external CRM via webhook."""
        config = funnel.external_crm_config
        if not config:
            raise ValidationError("Keine externe CRM-Konfiguration vorhanden")

        crm_type = config.get("type", "webhook")
        handoff.external_crm_type = crm_type

        # Prepare payload
        payload = {
            "prospect": {
                "id": prospect.id,
                "name": prospect.name,
                "email": prospect.email,
                "phone": prospect.phone,
                "mobile": prospect.mobile,
                "position": prospect.position,
                "linkedin_url": prospect.linkedin_url,
                "twitter_url": prospect.twitter_url,
                "score": prospect.score,
                "tags": prospect.tags,
                "custom_fields": prospect.custom_fields,
            },
            "company": None,
            "funnel": {
                "id": funnel.id,
                "name": funnel.name,
            },
            "handoff": {
                "id": handoff.id,
                "create_deal": data.create_deal,
                "deal_title": data.deal_title,
                "deal_value": data.deal_value,
                "notes": data.notes,
            },
        }

        if prospect.company:
            payload["company"] = {
                "id": prospect.company.id,
                "name": prospect.company.name,
                "domain": prospect.company.domain,
                "industry": prospect.company.industry,
                "size": prospect.company.size,
            }

        # Apply field mapping if configured
        if config.get("field_mapping"):
            payload = self._apply_field_mapping(payload, config["field_mapping"])

        # Send to webhook
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            raise ValidationError("Keine Webhook-URL konfiguriert")

        async with httpx.AsyncClient() as client:
            headers = {"Content-Type": "application/json"}
            if config.get("api_key"):
                headers["Authorization"] = f"Bearer {config['api_key']}"

            response = await client.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()

            # Parse response for external IDs
            result = response.json()
            if result.get("contact_id"):
                handoff.external_crm_contact_id = str(result["contact_id"])
            if result.get("deal_id"):
                handoff.external_crm_deal_id = str(result["deal_id"])

        logger.info(
            "Externes Handoff abgeschlossen: Prospect {id} -> {crm}",
            id=prospect.id,
            crm=crm_type,
        )

    def _apply_field_mapping(
        self, payload: dict, mapping: dict
    ) -> dict:
        """Apply field mapping to payload."""
        # Simple field mapping implementation
        # Could be extended for more complex mappings
        return payload

    def _create_prospect_snapshot(self, prospect: FunnelProspect) -> dict:
        """Create a snapshot of prospect data for the handoff record."""
        return {
            "id": prospect.id,
            "name": prospect.name,
            "email": prospect.email,
            "phone": prospect.phone,
            "mobile": prospect.mobile,
            "position": prospect.position,
            "linkedin_url": prospect.linkedin_url,
            "score": prospect.score,
            "status": prospect.status,
            "tags": prospect.tags,
            "custom_fields": prospect.custom_fields,
            "company_id": prospect.company_id,
            "company_name": prospect.company.name if prospect.company else None,
        }

    async def retry_handoff(
        self, tenant_id: str, handoff_id: int, user_id: int | None = None
    ) -> FunnelHandoff:
        """Retry a failed handoff."""
        result = await self.db.execute(
            select(FunnelHandoff)
            .options(selectinload(FunnelHandoff.prospect))
            .where(
                FunnelHandoff.id == handoff_id,
                FunnelHandoff.tenant_id == tenant_id,
            )
        )
        handoff = result.scalar_one_or_none()
        if not handoff:
            raise NotFoundError("Handoff", handoff_id)

        if handoff.status != "failed":
            raise ValidationError("Nur fehlgeschlagene Handoffs können wiederholt werden")

        # Reset status and retry
        handoff.status = "processing"
        handoff.error_message = None

        # Get original prospect data from snapshot or fresh
        prospect = handoff.prospect
        if not prospect:
            raise ValidationError("Prospect nicht mehr vorhanden")

        try:
            await self._process_handoff(
                handoff,
                prospect,
                HandoffInitiateRequest(create_deal=True),
                user_id,
            )
            handoff.status = "completed"
            handoff.completed_at = datetime.utcnow()
            prospect.status = "handed_off"
        except Exception as e:
            logger.exception("Handoff Retry fehlgeschlagen: {err}", err=str(e))
            handoff.status = "failed"
            handoff.error_message = str(e)
            handoff.retry_count += 1

        await self.db.flush()
        await self.db.refresh(handoff)
        return handoff

    async def list_handoffs(
        self,
        tenant_id: str,
        funnel_id: int | None = None,
        status: str | None = None,
    ) -> list[FunnelHandoff]:
        """List handoffs with optional filters."""
        query = (
            select(FunnelHandoff)
            .options(
                selectinload(FunnelHandoff.prospect),
                selectinload(FunnelHandoff.company),
            )
            .where(FunnelHandoff.tenant_id == tenant_id)
        )

        if funnel_id:
            query = query.where(FunnelHandoff.funnel_id == funnel_id)
        if status:
            query = query.where(FunnelHandoff.status == status)

        query = query.order_by(FunnelHandoff.triggered_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
