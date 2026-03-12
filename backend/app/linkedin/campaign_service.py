"""LinkedIn campaign service - Campaign management and execution."""

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInCampaign,
    LinkedInCampaignLead,
    LinkedInCampaignStep,
    LinkedInConnection,
    LinkedInContact,
    LinkedInMessage,
)
from app.linkedin.schemas import (
    LinkedInCampaignCreate,
    LinkedInCampaignLeadBulkCreate,
    LinkedInCampaignLeadBulkResult,
    LinkedInCampaignLeadCreate,
    LinkedInCampaignStepCreate,
    LinkedInCampaignUpdate,
)


class CampaignService:
    """Service for campaign management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: LinkedInCampaignCreate
    ) -> LinkedInCampaign:
        """Create a new campaign."""
        # Validate account
        account_result = await self.db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == data.account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise NotFoundError("LinkedInAccount", data.account_id)

        campaign = LinkedInCampaign(
            tenant_id=tenant_id,
            account_id=data.account_id,
            name=data.name,
            description=data.description,
            timezone=data.timezone,
            daily_connection_limit=data.daily_connection_limit,
            daily_message_limit=data.daily_message_limit,
            schedule_days=data.schedule_days,
            schedule_start_time=data.schedule_start_time,
            schedule_end_time=data.schedule_end_time,
            stop_on_reply=data.stop_on_reply,
            stop_on_connect=data.stop_on_connect,
            status="draft",
        )
        self.db.add(campaign)
        await self.db.flush()

        # Create steps if provided
        if data.steps:
            for step_data in data.steps:
                step = LinkedInCampaignStep(
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    name=step_data.name,
                    order=step_data.order,
                    step_type=step_data.step_type,
                    wait_days=step_data.wait_days,
                    wait_hours=step_data.wait_hours,
                    template_id=step_data.template_id,
                    template_ids=step_data.template_ids,
                    ab_test_enabled=step_data.ab_test_enabled,
                    condition_type=step_data.condition_type,
                    condition_true_step_id=step_data.condition_true_step_id,
                    condition_false_step_id=step_data.condition_false_step_id,
                )
                self.db.add(step)

        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("Campaign erstellt: {name}", name=data.name)
        return campaign

    async def get_by_id(self, tenant_id: str, campaign_id: int) -> LinkedInCampaign:
        """Get a campaign by ID."""
        result = await self.db.execute(
            select(LinkedInCampaign)
            .options(
                selectinload(LinkedInCampaign.account),
                selectinload(LinkedInCampaign.steps).selectinload(LinkedInCampaignStep.template),
            )
            .where(
                LinkedInCampaign.id == campaign_id,
                LinkedInCampaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("LinkedInCampaign", campaign_id)
        return campaign

    async def list_campaigns(
        self,
        tenant_id: str,
        account_id: int | None = None,
        status: str | None = None,
        pipeline_id: int | None = None,
    ) -> list[LinkedInCampaign]:
        """List all campaigns."""
        query = (
            select(LinkedInCampaign)
            .options(selectinload(LinkedInCampaign.account))
            .where(LinkedInCampaign.tenant_id == tenant_id)
        )

        if account_id:
            query = query.where(LinkedInCampaign.account_id == account_id)
        if status:
            query = query.where(LinkedInCampaign.status == status)
        if pipeline_id is not None:
            query = query.where(LinkedInCampaign.pipeline_id == pipeline_id)

        query = query.order_by(LinkedInCampaign.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, campaign_id: int, data: LinkedInCampaignUpdate
    ) -> LinkedInCampaign:
        """Update a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status == "active" and data.status not in ["paused", "active", None]:
            raise ValidationError("Aktive Kampagne kann nur pausiert werden")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(campaign, key, value)

        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("Campaign aktualisiert: {id}", id=campaign_id)
        return campaign

    async def delete(self, tenant_id: str, campaign_id: int) -> None:
        """Delete a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status == "active":
            raise ValidationError("Aktive Kampagne kann nicht gelöscht werden")

        await self.db.delete(campaign)
        await self.db.flush()
        logger.info("Campaign gelöscht: {id}", id=campaign_id)

    async def start(self, tenant_id: str, campaign_id: int) -> LinkedInCampaign:
        """Start a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status not in ["draft", "paused"]:
            raise ValidationError(f"Kampagne kann nicht gestartet werden (Status: {campaign.status})")

        if not campaign.steps:
            raise ValidationError("Kampagne hat keine Schritte definiert")

        # Check account is active
        if campaign.account.status != "active":
            raise ValidationError("Account ist nicht aktiv")

        campaign.status = "active"
        if not campaign.started_at:
            campaign.started_at = datetime.utcnow()

        # Activate pending leads
        leads_result = await self.db.execute(
            select(LinkedInCampaignLead).where(
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.status == "pending",
            )
        )
        pending_leads = list(leads_result.scalars().all())

        first_step = min(campaign.steps, key=lambda s: s.order, default=None)
        for lead in pending_leads:
            lead.status = "active"
            if first_step:
                lead.current_step_id = first_step.id
                lead.current_step_order = first_step.order
            lead.next_action_at = datetime.utcnow()

        campaign.leads_active = len(pending_leads)
        await self.db.flush()
        await self.db.refresh(campaign)

        logger.info("Campaign gestartet: {id} mit {leads} Leads", id=campaign_id, leads=len(pending_leads))
        return campaign

    async def pause(self, tenant_id: str, campaign_id: int) -> LinkedInCampaign:
        """Pause a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status != "active":
            raise ValidationError("Nur aktive Kampagnen können pausiert werden")

        campaign.status = "paused"
        await self.db.flush()
        await self.db.refresh(campaign)

        logger.info("Campaign pausiert: {id}", id=campaign_id)
        return campaign

    async def complete(self, tenant_id: str, campaign_id: int) -> LinkedInCampaign:
        """Mark campaign as completed."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(campaign)

        logger.info("Campaign abgeschlossen: {id}", id=campaign_id)
        return campaign

    # ============== Step Management ==============

    async def add_step(
        self, tenant_id: str, campaign_id: int, data: LinkedInCampaignStepCreate
    ) -> LinkedInCampaignStep:
        """Add a step to a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status == "active":
            raise ValidationError("Schritte können nicht zu aktiven Kampagnen hinzugefügt werden")

        step = LinkedInCampaignStep(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            name=data.name,
            order=data.order,
            step_type=data.step_type,
            wait_days=data.wait_days,
            wait_hours=data.wait_hours,
            template_id=data.template_id,
            template_ids=data.template_ids,
            ab_test_enabled=data.ab_test_enabled,
            condition_type=data.condition_type,
            condition_true_step_id=data.condition_true_step_id,
            condition_false_step_id=data.condition_false_step_id,
        )
        self.db.add(step)
        await self.db.flush()
        await self.db.refresh(step)

        logger.info("Step hinzugefügt: {name} zu Campaign {campaign}", name=data.name, campaign=campaign_id)
        return step

    async def update_step(
        self,
        tenant_id: str,
        campaign_id: int,
        step_id: int,
        data: LinkedInCampaignStepCreate,
    ) -> LinkedInCampaignStep:
        """Update a campaign step."""
        await self.get_by_id(tenant_id, campaign_id)  # Validate campaign exists

        result = await self.db.execute(
            select(LinkedInCampaignStep).where(
                LinkedInCampaignStep.id == step_id,
                LinkedInCampaignStep.campaign_id == campaign_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise NotFoundError("LinkedInCampaignStep", step_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(step, key, value)

        await self.db.flush()
        await self.db.refresh(step)
        return step

    async def delete_step(
        self, tenant_id: str, campaign_id: int, step_id: int
    ) -> None:
        """Delete a campaign step."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status == "active":
            raise ValidationError("Schritte können nicht aus aktiven Kampagnen gelöscht werden")

        result = await self.db.execute(
            select(LinkedInCampaignStep).where(
                LinkedInCampaignStep.id == step_id,
                LinkedInCampaignStep.campaign_id == campaign_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise NotFoundError("LinkedInCampaignStep", step_id)

        await self.db.delete(step)
        await self.db.flush()

    # ============== Lead Management ==============

    async def add_lead(
        self, tenant_id: str, campaign_id: int, data: LinkedInCampaignLeadCreate
    ) -> LinkedInCampaignLead:
        """Add a lead to a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        # Check for duplicate
        existing = await self.db.execute(
            select(LinkedInCampaignLead).where(
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.linkedin_url == data.linkedin_url,
            )
        )
        if existing.scalar_one_or_none():
            raise ValidationError("Lead bereits in Kampagne vorhanden")

        lead = LinkedInCampaignLead(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            contact_id=data.contact_id,
            linkedin_url=data.linkedin_url,
            profile_name=data.profile_name,
            profile_headline=data.profile_headline,
            company_name=data.company_name,
            profile_picture_url=data.profile_picture_url,
            custom_variables=data.custom_variables,
            status="pending" if campaign.status == "draft" else "active",
            entered_campaign_at=datetime.utcnow(),
        )

        # Set first step if campaign is active
        if campaign.status == "active" and campaign.steps:
            first_step = min(campaign.steps, key=lambda s: s.order)
            lead.current_step_id = first_step.id
            lead.current_step_order = first_step.order
            lead.next_action_at = datetime.utcnow()
            lead.status = "active"

        self.db.add(lead)
        campaign.total_leads += 1
        if lead.status == "active":
            campaign.leads_active += 1

        await self.db.flush()
        await self.db.refresh(lead)

        logger.info("Lead hinzugefügt: {name} zu Campaign {campaign}", name=data.profile_name, campaign=campaign_id)
        return lead

    async def add_leads_bulk(
        self, tenant_id: str, campaign_id: int, data: LinkedInCampaignLeadBulkCreate
    ) -> LinkedInCampaignLeadBulkResult:
        """Add multiple leads from contacts."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        # Get contacts
        contacts_result = await self.db.execute(
            select(LinkedInContact).where(
                LinkedInContact.tenant_id == tenant_id,
                LinkedInContact.id.in_(data.contact_ids),
            )
        )
        contacts = list(contacts_result.scalars().all())

        # Get existing leads
        existing_result = await self.db.execute(
            select(LinkedInCampaignLead.linkedin_url).where(
                LinkedInCampaignLead.campaign_id == campaign_id
            )
        )
        existing_urls = set(row[0] for row in existing_result.all())

        added = 0
        skipped = 0
        duplicates = 0
        errors = []

        first_step = min(campaign.steps, key=lambda s: s.order) if campaign.steps else None

        for contact in contacts:
            try:
                if contact.linkedin_url in existing_urls:
                    duplicates += 1
                    continue

                lead = LinkedInCampaignLead(
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    contact_id=contact.id,
                    linkedin_url=contact.linkedin_url,
                    linkedin_id=contact.linkedin_id,
                    profile_name=contact.name,
                    profile_headline=contact.headline,
                    company_name=contact.company_name,
                    profile_picture_url=contact.profile_picture_url,
                    custom_variables={
                        **(data.custom_variables or {}),
                        "first_name": contact.first_name or contact.name.split()[0],
                        "last_name": contact.last_name or "",
                        "company": contact.company_name or "",
                        "position": contact.position or "",
                    },
                    status="pending" if campaign.status == "draft" else "active",
                    entered_campaign_at=datetime.utcnow(),
                )

                if campaign.status == "active" and first_step:
                    lead.current_step_id = first_step.id
                    lead.current_step_order = first_step.order
                    lead.next_action_at = datetime.utcnow()
                    lead.status = "active"

                self.db.add(lead)
                existing_urls.add(contact.linkedin_url)
                added += 1

            except Exception as e:
                errors.append(f"{contact.name}: {e!s}")
                skipped += 1

        campaign.total_leads += added
        if campaign.status == "active":
            campaign.leads_active += added

        await self.db.flush()

        logger.info(
            "Bulk leads hinzugefügt: {added} zu Campaign {campaign}",
            added=added,
            campaign=campaign_id,
        )

        return LinkedInCampaignLeadBulkResult(
            total=len(data.contact_ids),
            added=added,
            skipped=skipped,
            duplicates=duplicates,
            errors=errors[:10],
        )

    async def list_leads(
        self,
        tenant_id: str,
        campaign_id: int,
        status: str | None = None,
    ) -> list[LinkedInCampaignLead]:
        """List leads in a campaign."""
        query = (
            select(LinkedInCampaignLead)
            .options(selectinload(LinkedInCampaignLead.current_step))
            .where(
                LinkedInCampaignLead.tenant_id == tenant_id,
                LinkedInCampaignLead.campaign_id == campaign_id,
            )
        )

        if status:
            query = query.where(LinkedInCampaignLead.status == status)

        query = query.order_by(LinkedInCampaignLead.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_lead(
        self, tenant_id: str, campaign_id: int, lead_id: int
    ) -> LinkedInCampaignLead:
        """Get a campaign lead."""
        result = await self.db.execute(
            select(LinkedInCampaignLead)
            .options(selectinload(LinkedInCampaignLead.current_step))
            .where(
                LinkedInCampaignLead.id == lead_id,
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.tenant_id == tenant_id,
            )
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise NotFoundError("LinkedInCampaignLead", lead_id)
        return lead

    async def remove_lead(
        self, tenant_id: str, campaign_id: int, lead_id: int
    ) -> None:
        """Remove a lead from campaign."""
        lead = await self.get_lead(tenant_id, campaign_id, lead_id)

        campaign = await self.get_by_id(tenant_id, campaign_id)
        campaign.total_leads -= 1
        if lead.status == "active":
            campaign.leads_active -= 1

        await self.db.delete(lead)
        await self.db.flush()

    async def stop_lead(
        self, tenant_id: str, campaign_id: int, lead_id: int, reason: str = "manual"
    ) -> LinkedInCampaignLead:
        """Stop a lead in campaign."""
        lead = await self.get_lead(tenant_id, campaign_id, lead_id)

        if lead.status == "active":
            campaign = await self.get_by_id(tenant_id, campaign_id)
            campaign.leads_active -= 1

        lead.status = "stopped"
        lead.error_message = f"Gestoppt: {reason}"
        lead.completed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(lead)
        return lead

    # ============== Execution ==============

    async def get_leads_ready_for_action(
        self, campaign_id: int, limit: int = 10
    ) -> list[LinkedInCampaignLead]:
        """Get leads that are ready for their next action."""
        result = await self.db.execute(
            select(LinkedInCampaignLead)
            .options(
                selectinload(LinkedInCampaignLead.current_step),
                selectinload(LinkedInCampaignLead.campaign),
            )
            .where(
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.status == "active",
                LinkedInCampaignLead.next_action_at <= datetime.utcnow(),
            )
            .order_by(LinkedInCampaignLead.next_action_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def advance_lead_to_next_step(
        self, lead: LinkedInCampaignLead
    ) -> LinkedInCampaignLead:
        """Move lead to the next step in campaign."""
        campaign_result = await self.db.execute(
            select(LinkedInCampaign)
            .options(selectinload(LinkedInCampaign.steps))
            .where(LinkedInCampaign.id == lead.campaign_id)
        )
        campaign = campaign_result.scalar_one()

        # Complete current step stats
        if lead.current_step_id:
            step_result = await self.db.execute(
                select(LinkedInCampaignStep).where(
                    LinkedInCampaignStep.id == lead.current_step_id
                )
            )
            current_step = step_result.scalar_one_or_none()
            if current_step:
                current_step.leads_completed += 1

        # Find next step
        sorted_steps = sorted(campaign.steps, key=lambda s: s.order)
        current_order = lead.current_step_order
        next_step = None

        for step in sorted_steps:
            if step.order > current_order and step.is_active:
                next_step = step
                break

        if next_step:
            lead.current_step_id = next_step.id
            lead.current_step_order = next_step.order
            next_step.leads_entered += 1

            # Calculate next action time
            if next_step.step_type == "wait":
                wait_time = timedelta(
                    days=next_step.wait_days or 0,
                    hours=next_step.wait_hours or 0,
                )
                lead.next_action_at = datetime.utcnow() + wait_time
                lead.status = "waiting"
            else:
                lead.next_action_at = datetime.utcnow()
                lead.status = "active"
        else:
            # No more steps - campaign completed for this lead
            lead.status = "completed"
            lead.completed_at = datetime.utcnow()
            lead.next_action_at = None
            campaign.leads_completed += 1
            campaign.leads_active -= 1

        await self.db.flush()
        await self.db.refresh(lead)
        return lead

    async def mark_lead_replied(self, lead: LinkedInCampaignLead) -> LinkedInCampaignLead:
        """Mark a lead as having replied."""
        lead.has_replied = True
        lead.reply_received_at = datetime.utcnow()

        campaign = await self.get_by_id(lead.tenant_id, lead.campaign_id)
        campaign.replies_received += 1

        if campaign.stop_on_reply:
            lead.status = "replied"
            lead.completed_at = datetime.utcnow()
            lead.next_action_at = None
            campaign.leads_active -= 1
            campaign.leads_completed += 1

        await self.db.flush()
        await self.db.refresh(lead)
        return lead

    async def mark_lead_connected(self, lead: LinkedInCampaignLead) -> LinkedInCampaignLead:
        """Mark a lead as connected."""
        lead.connection_status = "accepted"

        campaign = await self.get_by_id(lead.tenant_id, lead.campaign_id)
        campaign.connections_accepted += 1

        if campaign.stop_on_connect:
            lead.status = "connected"
            lead.completed_at = datetime.utcnow()
            lead.next_action_at = None
            campaign.leads_active -= 1
            campaign.leads_completed += 1

        await self.db.flush()
        await self.db.refresh(lead)
        return lead

    async def update_campaign_stats(self, campaign_id: int) -> None:
        """Refresh campaign statistics from actual data."""
        campaign_result = await self.db.execute(
            select(LinkedInCampaign).where(LinkedInCampaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if not campaign:
            return

        # Count leads by status
        leads_result = await self.db.execute(
            select(
                LinkedInCampaignLead.status,
                func.count(LinkedInCampaignLead.id),
            )
            .where(LinkedInCampaignLead.campaign_id == campaign_id)
            .group_by(LinkedInCampaignLead.status)
        )
        status_counts = dict(leads_result.all())

        campaign.total_leads = sum(status_counts.values())
        campaign.leads_active = status_counts.get("active", 0) + status_counts.get("waiting", 0)
        campaign.leads_completed = (
            status_counts.get("completed", 0)
            + status_counts.get("replied", 0)
            + status_counts.get("connected", 0)
        )

        # Count connections
        conn_result = await self.db.execute(
            select(
                LinkedInConnection.status,
                func.count(LinkedInConnection.id),
            )
            .where(LinkedInConnection.campaign_id == campaign_id)
            .group_by(LinkedInConnection.status)
        )
        conn_counts = dict(conn_result.all())

        campaign.connections_sent = sum(
            conn_counts.get(s, 0) for s in ["sent", "accepted", "declined"]
        )
        campaign.connections_accepted = conn_counts.get("accepted", 0)

        # Count messages
        msg_result = await self.db.execute(
            select(func.count(LinkedInMessage.id)).where(
                LinkedInMessage.campaign_id == campaign_id,
                LinkedInMessage.direction == "outbound",
                LinkedInMessage.status.in_(["sent", "delivered", "read", "replied"]),
            )
        )
        campaign.messages_sent = msg_result.scalar() or 0

        # Count replies
        replies_result = await self.db.execute(
            select(func.count(LinkedInCampaignLead.id)).where(
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.has_replied.is_(True),
            )
        )
        campaign.replies_received = replies_result.scalar() or 0

        await self.db.flush()
