"""Email Marketing service - business logic for campaigns, sequences, tracking."""

import random
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.contacts.models import Contact
from app.emailmarketing.encryption import encrypt_api_key
from app.emailmarketing.models import (
    EmailCampaign,
    EmailClick,
    EmailProvider,
    EmailRecipient,
    EmailSequence,
    EmailSequenceEnrollment,
    EmailSequenceStep,
    EmailTemplate,
    EmailUnsubscribe,
)
from app.emailmarketing.providers import EmailMessage, get_provider
from app.emailmarketing.schemas import (
    CampaignStats,
    EmailCampaignCreate,
    EmailCampaignUpdate,
    EmailProviderCreate,
    EmailProviderUpdate,
    EmailSequenceCreate,
    EmailSequenceStepCreate,
    EmailSequenceStepUpdate,
    EmailSequenceUpdate,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    RecipientListParams,
)
from app.emailmarketing.tracking import process_email_content
from app.engagement import (
    EmailActivityType,
    log_email_activity,
)
from app.exceptions import AppError, DuplicateError, NotFoundError


class EmailProviderService:
    """Service for email provider management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: EmailProviderCreate) -> EmailProvider:
        """Create a new email provider."""
        # Encrypt the API key before storing
        encrypted_key = encrypt_api_key(data.api_key) if data.api_key else None

        provider = EmailProvider(
            tenant_id=tenant_id,
            provider_type=data.provider_type,
            api_key_encrypted=encrypted_key,
            sender_email=data.sender_email,
            sender_name=data.sender_name,
            reply_to_email=data.reply_to_email,
            tracking_domain=data.tracking_domain,
            hourly_limit=data.hourly_limit,
            daily_limit=data.daily_limit,
        )
        self.db.add(provider)
        await self.db.flush()
        await self.db.refresh(provider)
        logger.info(
            "E-Mail Provider erstellt: {type} ({email})",
            type=data.provider_type,
            email=data.sender_email,
        )
        return provider

    async def get_by_id(self, tenant_id: str, provider_id: int) -> EmailProvider:
        """Get provider by ID."""
        result = await self.db.execute(
            select(EmailProvider).where(
                EmailProvider.id == provider_id, EmailProvider.tenant_id == tenant_id
            )
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise NotFoundError("EmailProvider", provider_id)
        return provider

    async def list_providers(self, tenant_id: str) -> list[EmailProvider]:
        """List all providers for a tenant."""
        result = await self.db.execute(
            select(EmailProvider)
            .where(EmailProvider.tenant_id == tenant_id)
            .order_by(EmailProvider.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, provider_id: int, data: EmailProviderUpdate
    ) -> EmailProvider:
        """Update a provider."""
        provider = await self.get_by_id(tenant_id, provider_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle API key separately - encrypt before storing
        if update_data.get("api_key"):
            provider.api_key_encrypted = encrypt_api_key(update_data.pop("api_key"))

        for key, value in update_data.items():
            if hasattr(provider, key):
                setattr(provider, key, value)

        await self.db.flush()
        await self.db.refresh(provider)
        logger.info("E-Mail Provider aktualisiert: {id}", id=provider_id)
        return provider

    async def delete(self, tenant_id: str, provider_id: int) -> None:
        """Delete a provider."""
        provider = await self.get_by_id(tenant_id, provider_id)
        await self.db.delete(provider)
        await self.db.flush()
        logger.info("E-Mail Provider gelöscht: {id}", id=provider_id)

    async def verify(self, tenant_id: str, provider_id: int) -> bool:
        """Verify provider credentials."""
        provider = await self.get_by_id(tenant_id, provider_id)
        email_provider = get_provider(provider)

        try:
            valid = await email_provider.verify_credentials()
            provider.last_verified_at = datetime.utcnow()
            if valid:
                provider.status = "active"
                provider.last_error = None
            else:
                provider.status = "error"
                provider.last_error = "Credentials verification failed"
            await self.db.flush()
            return valid
        except Exception as e:
            provider.status = "error"
            provider.last_error = str(e)
            await self.db.flush()
            return False


class EmailTemplateService:
    """Service for email template management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: EmailTemplateCreate) -> EmailTemplate:
        """Create a new template."""
        # Check for duplicate slug
        existing = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.tenant_id == tenant_id, EmailTemplate.slug == data.slug
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("EmailTemplate", "slug")

        template = EmailTemplate(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            subject=data.subject,
            html_content=data.html_content,
            text_content=data.text_content,
            variables=data.variables,
            category=data.category,
            tags=data.tags,
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        logger.info("E-Mail Template erstellt: {name}", name=data.name)
        return template

    async def get_by_id(self, tenant_id: str, template_id: int) -> EmailTemplate:
        """Get template by ID."""
        result = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.id == template_id, EmailTemplate.tenant_id == tenant_id
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise NotFoundError("EmailTemplate", template_id)
        return template

    async def list_templates(
        self, tenant_id: str, active_only: bool = False
    ) -> list[EmailTemplate]:
        """List all templates for a tenant."""
        query = select(EmailTemplate).where(EmailTemplate.tenant_id == tenant_id)
        if active_only:
            query = query.where(EmailTemplate.is_active.is_(True))
        query = query.order_by(EmailTemplate.name)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, template_id: int, data: EmailTemplateUpdate
    ) -> EmailTemplate:
        """Update a template."""
        template = await self.get_by_id(tenant_id, template_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        await self.db.flush()
        await self.db.refresh(template)
        logger.info("E-Mail Template aktualisiert: {id}", id=template_id)
        return template

    async def delete(self, tenant_id: str, template_id: int) -> None:
        """Delete a template."""
        template = await self.get_by_id(tenant_id, template_id)
        await self.db.delete(template)
        await self.db.flush()
        logger.info("E-Mail Template gelöscht: {id}", id=template_id)


class EmailCampaignService:
    """Service for email campaign management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: EmailCampaignCreate) -> EmailCampaign:
        """Create a new campaign."""
        campaign = EmailCampaign(
            tenant_id=tenant_id,
            provider_id=data.provider_id,
            template_id=data.template_id,
            name=data.name,
            subject=data.subject,
            html_content=data.html_content,
            text_content=data.text_content,
            segment_filters=data.segment_filters,
            contact_ids=data.contact_ids,
            # A/B Testing
            ab_test_enabled=data.ab_test_enabled,
            ab_variant_b_subject=data.ab_variant_b_subject,
            ab_variant_b_html=data.ab_variant_b_html,
            ab_split_percentage=data.ab_split_percentage,
            ab_winner_metric=data.ab_winner_metric,
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("E-Mail Kampagne erstellt: {name}", name=data.name)
        return campaign

    async def get_by_id(self, tenant_id: str, campaign_id: int) -> EmailCampaign:
        """Get campaign by ID."""
        result = await self.db.execute(
            select(EmailCampaign)
            .options(
                selectinload(EmailCampaign.provider),
                selectinload(EmailCampaign.template),
            )
            .where(
                EmailCampaign.id == campaign_id, EmailCampaign.tenant_id == tenant_id
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("EmailCampaign", campaign_id)
        return campaign

    async def list_campaigns(
        self,
        tenant_id: str,
        status: str | None = None,
        pipeline_id: int | None = None,
    ) -> list[EmailCampaign]:
        """List campaigns for a tenant."""
        query = select(EmailCampaign).where(EmailCampaign.tenant_id == tenant_id)
        if status:
            query = query.where(EmailCampaign.status == status)
        if pipeline_id is not None:
            query = query.where(EmailCampaign.pipeline_id == pipeline_id)
        query = query.order_by(EmailCampaign.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, campaign_id: int, data: EmailCampaignUpdate
    ) -> EmailCampaign:
        """Update a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status not in ("draft", "scheduled"):
            raise AppError("Kampagne kann nicht mehr bearbeitet werden", 400)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(campaign, key, value)

        await self.db.flush()
        await self.db.refresh(campaign)
        logger.info("E-Mail Kampagne aktualisiert: {id}", id=campaign_id)
        return campaign

    async def delete(self, tenant_id: str, campaign_id: int) -> None:
        """Delete a campaign."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status == "sending":
            raise AppError("Laufende Kampagne kann nicht gelöscht werden", 400)

        await self.db.delete(campaign)
        await self.db.flush()
        logger.info("E-Mail Kampagne gelöscht: {id}", id=campaign_id)

    async def get_stats(self, tenant_id: str, campaign_id: int) -> CampaignStats:
        """Get detailed campaign statistics."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        total = campaign.total_recipients or 1  # Avoid division by zero

        # Calculate A/B rates
        ab_a_total = campaign.ab_a_sent or 1
        ab_b_total = campaign.ab_b_sent or 1

        return CampaignStats(
            total_recipients=campaign.total_recipients,
            sent=campaign.sent_count,
            delivered=campaign.delivered_count,
            opened=campaign.opened_count,
            clicked=campaign.clicked_count,
            bounced=campaign.bounced_count,
            unsubscribed=campaign.unsubscribed_count,
            spam=campaign.spam_count,
            open_rate=round((campaign.opened_count / total) * 100, 2),
            click_rate=round((campaign.clicked_count / total) * 100, 2),
            bounce_rate=round((campaign.bounced_count / total) * 100, 2),
            # A/B Testing stats
            ab_test_enabled=campaign.ab_test_enabled,
            ab_a_sent=campaign.ab_a_sent,
            ab_a_opened=campaign.ab_a_opened,
            ab_a_clicked=campaign.ab_a_clicked,
            ab_a_open_rate=round((campaign.ab_a_opened / ab_a_total) * 100, 2),
            ab_a_click_rate=round((campaign.ab_a_clicked / ab_a_total) * 100, 2),
            ab_b_sent=campaign.ab_b_sent,
            ab_b_opened=campaign.ab_b_opened,
            ab_b_clicked=campaign.ab_b_clicked,
            ab_b_open_rate=round((campaign.ab_b_opened / ab_b_total) * 100, 2),
            ab_b_click_rate=round((campaign.ab_b_clicked / ab_b_total) * 100, 2),
            ab_winner_variant=campaign.ab_winner_variant,
        )

    async def generate_recipients(
        self, tenant_id: str, campaign_id: int
    ) -> list[EmailRecipient]:
        """Generate recipient list from segment filters or contact IDs."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        # Build contact query
        query = select(Contact).where(Contact.tenant_id == tenant_id)

        # Apply segment filters
        if campaign.segment_filters:
            filters = campaign.segment_filters
            if filters.get("tags"):
                query = query.where(Contact.tags.op("?|")(filters["tags"]))
            if filters.get("source"):
                query = query.where(Contact.source == filters["source"])

        # Or use explicit contact IDs
        elif campaign.contact_ids:
            query = query.where(Contact.id.in_(campaign.contact_ids))

        result = await self.db.execute(query)
        contacts = list(result.scalars().all())

        # Check for unsubscribes
        unsubscribed_emails = await self._get_unsubscribed_emails(tenant_id)

        # Create recipients with optional A/B variant assignment
        recipients = []
        for contact in contacts:
            if contact.email in unsubscribed_emails:
                continue

            # Assign A/B variant if A/B testing is enabled
            ab_variant = None
            if campaign.ab_test_enabled:
                # Random assignment based on split percentage
                # ab_split_percentage is the % for variant A
                ab_variant = "A" if random.randint(1, 100) <= campaign.ab_split_percentage else "B"

            recipient = EmailRecipient(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                contact_id=contact.id,
                email=contact.email,
                name=contact.name,
                merge_data={
                    "name": contact.name,
                    "email": contact.email,
                    "phone": contact.phone or "",
                    "position": contact.position or "",
                },
                tracking_token=str(uuid.uuid4()),
                ab_variant=ab_variant,
            )
            self.db.add(recipient)
            recipients.append(recipient)

        campaign.total_recipients = len(recipients)
        await self.db.flush()

        logger.info(
            "Empfänger generiert: {count} für Kampagne {id}",
            count=len(recipients),
            id=campaign_id,
        )
        return recipients

    async def _get_unsubscribed_emails(self, tenant_id: str) -> set[str]:
        """Get set of unsubscribed emails."""
        result = await self.db.execute(
            select(EmailUnsubscribe.email).where(
                EmailUnsubscribe.tenant_id == tenant_id
            )
        )
        return {row[0] for row in result.all()}

    async def send_campaign(self, tenant_id: str, campaign_id: int) -> int:
        """Send campaign to all recipients."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status != "draft" and campaign.status != "scheduled":
            raise AppError("Kampagne ist bereits gesendet oder wird gesendet", 400)

        if not campaign.provider_id:
            raise AppError("Kein E-Mail Provider konfiguriert", 400)

        # Get provider
        provider_service = EmailProviderService(self.db)
        provider_model = await provider_service.get_by_id(
            tenant_id, campaign.provider_id
        )
        provider = get_provider(provider_model)

        # Get or generate recipients
        result = await self.db.execute(
            select(EmailRecipient).where(
                EmailRecipient.campaign_id == campaign_id,
                EmailRecipient.status == "pending",
            )
        )
        recipients = list(result.scalars().all())

        if not recipients:
            # Generate recipients
            recipients = await self.generate_recipients(tenant_id, campaign_id)

        # Update campaign status
        campaign.status = "sending"
        await self.db.flush()

        # Build tracking base URL
        base_tracking_url = settings.api_url or "http://localhost:8002/api/v1"

        # Send emails
        sent_count = 0
        messages = []

        for recipient in recipients:
            # Determine subject and HTML based on A/B variant
            if campaign.ab_test_enabled and recipient.ab_variant == "B":
                subject = campaign.ab_variant_b_subject or campaign.subject
                html_content = campaign.ab_variant_b_html or campaign.html_content
            else:
                subject = campaign.subject
                html_content = campaign.html_content

            # Process content with tracking
            html = process_email_content(
                html_content,
                recipient.tracking_token,
                base_tracking_url,
                recipient.merge_data,
            )

            message = EmailMessage(
                to_email=recipient.email,
                to_name=recipient.name,
                subject=subject,
                html_content=html,
                text_content=campaign.text_content,
                tracking_token=recipient.tracking_token,
            )
            messages.append((recipient, message))

        # Send in batches
        batch_size = 100
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            batch_messages = [msg for _, msg in batch]

            results = await provider.send_batch(batch_messages)

            for (recipient, _), result in zip(batch, results, strict=False):
                if result.success:
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    recipient.provider_message_id = result.message_id
                    sent_count += 1
                    # Track A/B stats
                    if campaign.ab_test_enabled:
                        if recipient.ab_variant == "A":
                            campaign.ab_a_sent += 1
                        elif recipient.ab_variant == "B":
                            campaign.ab_b_sent += 1
                else:
                    recipient.status = "bounced"
                    recipient.bounced_at = datetime.utcnow()
                    campaign.bounced_count += 1

            await self.db.flush()

        # Update campaign stats
        campaign.sent_count = sent_count
        campaign.status = "sent"
        campaign.sent_at = datetime.utcnow()
        await self.db.flush()

        logger.info(
            "Kampagne gesendet: {id}, {count} E-Mails",
            id=campaign_id,
            count=sent_count,
        )
        return sent_count

    async def send_test(
        self, tenant_id: str, campaign_id: int, to_email: str, merge_data: dict
    ) -> bool:
        """Send a test email."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if not campaign.provider_id:
            raise AppError("Kein E-Mail Provider konfiguriert", 400)

        # Get provider
        provider_service = EmailProviderService(self.db)
        provider_model = await provider_service.get_by_id(
            tenant_id, campaign.provider_id
        )
        provider = get_provider(provider_model)

        # Generate test tracking token
        test_token = str(uuid.uuid4())

        # Build tracking base URL
        base_tracking_url = settings.api_url or "http://localhost:8002/api/v1"

        # Process content
        html = process_email_content(
            campaign.html_content,
            test_token,
            base_tracking_url,
            merge_data,
        )

        message = EmailMessage(
            to_email=to_email,
            to_name=merge_data.get("name"),
            subject=f"[TEST] {campaign.subject}",
            html_content=html,
            text_content=campaign.text_content,
        )

        result = await provider.send_email(message)

        if not result.success:
            raise AppError(f"Test-E-Mail fehlgeschlagen: {result.error}", 500)

        return True

    async def send_single_email(
        self,
        tenant_id: str,
        to_email: str,
        to_name: str | None,
        subject: str,
        body: str,
        provider_id: int | None = None,
    ) -> dict:
        """Send a single email directly.

        Used by engagement actions to send one-off emails.

        Args:
            tenant_id: Tenant ID
            to_email: Recipient email
            to_name: Recipient name
            subject: Email subject
            body: Email body (HTML)
            provider_id: Optional provider ID (uses first active if not specified)

        Returns:
            Dict with send result
        """
        # Get provider
        provider_service = EmailProviderService(self.db)

        if provider_id:
            provider_model = await provider_service.get_by_id(tenant_id, provider_id)
        else:
            # Get first active provider
            providers = await provider_service.list_providers(tenant_id)
            active_providers = [p for p in providers if p.is_active]
            if not active_providers:
                raise AppError("Kein aktiver E-Mail Provider konfiguriert", 400)
            provider_model = active_providers[0]

        provider = get_provider(provider_model)

        message = EmailMessage(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=body,
            text_content=body,  # Simple fallback
        )

        result = await provider.send_email(message)

        if not result.success:
            raise AppError(f"E-Mail Versand fehlgeschlagen: {result.error}", 500)

        logger.info(
            "Single email sent: {to_email}, subject: {subject}",
            to_email=to_email,
            subject=subject[:50],
        )

        return {
            "success": True,
            "message_id": result.message_id,
            "to_email": to_email,
        }

    async def schedule_campaign(
        self, tenant_id: str, campaign_id: int, scheduled_at: datetime
    ) -> EmailCampaign:
        """Schedule campaign for later sending."""
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if campaign.status != "draft":
            raise AppError("Nur Entwürfe können geplant werden", 400)

        campaign.status = "scheduled"
        campaign.scheduled_at = scheduled_at
        await self.db.flush()
        await self.db.refresh(campaign)

        logger.info(
            "Kampagne geplant: {id} für {time}",
            id=campaign_id,
            time=scheduled_at.isoformat(),
        )
        return campaign

    async def get_recipients(
        self, tenant_id: str, campaign_id: int, params: RecipientListParams
    ) -> tuple[list[EmailRecipient], int]:
        """Get recipients for a campaign."""
        # Ensure campaign exists
        await self.get_by_id(tenant_id, campaign_id)

        query = select(EmailRecipient).where(
            EmailRecipient.campaign_id == campaign_id,
            EmailRecipient.tenant_id == tenant_id,
        )

        if params.status:
            query = query.where(EmailRecipient.status == params.status)
        if params.search:
            search_term = f"%{params.search}%"
            query = query.where(
                or_(
                    EmailRecipient.email.ilike(search_term),
                    EmailRecipient.name.ilike(search_term),
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        query = query.order_by(EmailRecipient.created_at.desc())
        query = query.offset(params.offset).limit(params.limit)

        result = await self.db.execute(query)
        recipients = list(result.scalars().all())

        return recipients, total


class EmailSequenceService:
    """Service for email sequence management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: EmailSequenceCreate
    ) -> EmailSequence:
        """Create a new sequence."""
        sequence = EmailSequence(
            tenant_id=tenant_id,
            provider_id=data.provider_id,
            name=data.name,
            description=data.description,
            trigger_type=data.trigger_type,
            trigger_filters=data.trigger_filters,
            send_window_start=data.send_window_start,
            send_window_end=data.send_window_end,
            skip_weekends=data.skip_weekends,
            timezone=data.timezone,
        )
        self.db.add(sequence)
        await self.db.flush()
        await self.db.refresh(sequence)
        logger.info("E-Mail Sequenz erstellt: {name}", name=data.name)
        return sequence

    async def get_by_id(self, tenant_id: str, sequence_id: int) -> EmailSequence:
        """Get sequence by ID with steps."""
        result = await self.db.execute(
            select(EmailSequence)
            .options(selectinload(EmailSequence.steps))
            .where(
                EmailSequence.id == sequence_id, EmailSequence.tenant_id == tenant_id
            )
        )
        sequence = result.scalar_one_or_none()
        if not sequence:
            raise NotFoundError("EmailSequence", sequence_id)
        return sequence

    async def list_sequences(
        self,
        tenant_id: str,
        status: str | None = None,
        pipeline_id: int | None = None,
    ) -> list[dict]:
        """List sequences with step count."""
        query = select(EmailSequence).where(EmailSequence.tenant_id == tenant_id)
        if status:
            query = query.where(EmailSequence.status == status)
        if pipeline_id is not None:
            query = query.where(EmailSequence.pipeline_id == pipeline_id)
        query = query.order_by(EmailSequence.created_at.desc())

        result = await self.db.execute(query)
        sequences = list(result.scalars().all())

        # Get step counts
        step_counts = {}
        if sequences:
            seq_ids = [s.id for s in sequences]
            count_result = await self.db.execute(
                select(
                    EmailSequenceStep.sequence_id,
                    func.count(EmailSequenceStep.id).label("count"),
                )
                .where(EmailSequenceStep.sequence_id.in_(seq_ids))
                .group_by(EmailSequenceStep.sequence_id)
            )
            step_counts = {row[0]: row[1] for row in count_result.all()}

        # Build response with step counts
        return [
            {
                "id": s.id,
                "name": s.name,
                "trigger_type": s.trigger_type,
                "status": s.status,
                "total_enrolled": s.total_enrolled,
                "total_completed": s.total_completed,
                "step_count": step_counts.get(s.id, 0),
                "created_at": s.created_at,
            }
            for s in sequences
        ]

    async def update(
        self, tenant_id: str, sequence_id: int, data: EmailSequenceUpdate
    ) -> EmailSequence:
        """Update a sequence."""
        sequence = await self.get_by_id(tenant_id, sequence_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(sequence, key, value)

        await self.db.flush()
        await self.db.refresh(sequence)
        logger.info("E-Mail Sequenz aktualisiert: {id}", id=sequence_id)
        return sequence

    async def delete(self, tenant_id: str, sequence_id: int) -> None:
        """Delete a sequence."""
        sequence = await self.get_by_id(tenant_id, sequence_id)
        await self.db.delete(sequence)
        await self.db.flush()
        logger.info("E-Mail Sequenz gelöscht: {id}", id=sequence_id)

    async def activate(self, tenant_id: str, sequence_id: int) -> EmailSequence:
        """Activate a sequence."""
        sequence = await self.get_by_id(tenant_id, sequence_id)

        if not sequence.steps:
            raise AppError("Sequenz benötigt mindestens einen Schritt", 400)

        sequence.status = "active"
        await self.db.flush()
        await self.db.refresh(sequence)
        logger.info("E-Mail Sequenz aktiviert: {id}", id=sequence_id)
        return sequence

    async def pause(self, tenant_id: str, sequence_id: int) -> EmailSequence:
        """Pause a sequence."""
        sequence = await self.get_by_id(tenant_id, sequence_id)
        sequence.status = "paused"
        await self.db.flush()
        await self.db.refresh(sequence)
        logger.info("E-Mail Sequenz pausiert: {id}", id=sequence_id)
        return sequence

    # ============== Step Management ==============

    async def add_step(
        self, tenant_id: str, sequence_id: int, data: EmailSequenceStepCreate
    ) -> EmailSequenceStep:
        """Add a step to a sequence."""
        # Verify sequence exists
        await self.get_by_id(tenant_id, sequence_id)

        step = EmailSequenceStep(
            tenant_id=tenant_id,
            sequence_id=sequence_id,
            template_id=data.template_id,
            position=data.position,
            delay_days=data.delay_days,
            delay_hours=data.delay_hours,
            subject=data.subject,
            html_content=data.html_content,
            text_content=data.text_content,
            send_if_opened_previous=data.send_if_opened_previous,
            send_if_clicked_previous=data.send_if_clicked_previous,
        )
        self.db.add(step)
        await self.db.flush()
        await self.db.refresh(step)
        logger.info(
            "Sequenz-Schritt hinzugefügt: Sequenz {seq}, Position {pos}",
            seq=sequence_id,
            pos=data.position,
        )
        return step

    async def update_step(
        self,
        tenant_id: str,
        sequence_id: int,
        step_id: int,
        data: EmailSequenceStepUpdate,
    ) -> EmailSequenceStep:
        """Update a sequence step."""
        result = await self.db.execute(
            select(EmailSequenceStep).where(
                EmailSequenceStep.id == step_id,
                EmailSequenceStep.sequence_id == sequence_id,
                EmailSequenceStep.tenant_id == tenant_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise NotFoundError("EmailSequenceStep", step_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(step, key, value)

        await self.db.flush()
        await self.db.refresh(step)
        return step

    async def delete_step(
        self, tenant_id: str, sequence_id: int, step_id: int
    ) -> None:
        """Delete a sequence step."""
        result = await self.db.execute(
            select(EmailSequenceStep).where(
                EmailSequenceStep.id == step_id,
                EmailSequenceStep.sequence_id == sequence_id,
                EmailSequenceStep.tenant_id == tenant_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise NotFoundError("EmailSequenceStep", step_id)

        await self.db.delete(step)
        await self.db.flush()

    # ============== Enrollment Management ==============

    async def enroll_contacts(
        self, tenant_id: str, sequence_id: int, contact_ids: list[int]
    ) -> int:
        """Enroll contacts in a sequence."""
        sequence = await self.get_by_id(tenant_id, sequence_id)

        if sequence.status != "active":
            raise AppError("Sequenz ist nicht aktiv", 400)

        # Get existing enrollments
        existing = await self.db.execute(
            select(EmailSequenceEnrollment.contact_id).where(
                EmailSequenceEnrollment.sequence_id == sequence_id,
                EmailSequenceEnrollment.contact_id.in_(contact_ids),
            )
        )
        existing_ids = {row[0] for row in existing.all()}

        # Create enrollments for new contacts
        enrolled = 0
        for contact_id in contact_ids:
            if contact_id in existing_ids:
                continue

            enrollment = EmailSequenceEnrollment(
                tenant_id=tenant_id,
                sequence_id=sequence_id,
                contact_id=contact_id,
                enrolled_at=datetime.utcnow(),
                next_send_at=datetime.utcnow(),  # First step immediately
                source="manual",
            )
            self.db.add(enrollment)
            enrolled += 1

        sequence.total_enrolled += enrolled
        await self.db.flush()

        logger.info(
            "Kontakte eingeschrieben: {count} in Sequenz {id}",
            count=enrolled,
            id=sequence_id,
        )
        return enrolled

    async def get_enrollments(
        self, tenant_id: str, sequence_id: int, status: str | None = None
    ) -> list[EmailSequenceEnrollment]:
        """Get enrollments for a sequence."""
        query = (
            select(EmailSequenceEnrollment)
            .options(selectinload(EmailSequenceEnrollment.contact))
            .where(
                EmailSequenceEnrollment.sequence_id == sequence_id,
                EmailSequenceEnrollment.tenant_id == tenant_id,
            )
        )
        if status:
            query = query.where(EmailSequenceEnrollment.status == status)
        query = query.order_by(EmailSequenceEnrollment.enrolled_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())


class TrackingService:
    """Service for email tracking events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record_open(self, tracking_token: str, ip_address: str | None = None):
        """Record email open event."""
        result = await self.db.execute(
            select(EmailRecipient).where(
                EmailRecipient.tracking_token == tracking_token
            )
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            logger.warning("Open tracking: Token nicht gefunden {token}", token=tracking_token)
            return

        # Only record first open
        if not recipient.opened_at:
            recipient.opened_at = datetime.utcnow()
            recipient.status = "opened"

            # Update campaign stats
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(opened_count=EmailCampaign.opened_count + 1)
            )

            # Update A/B stats if applicable
            if recipient.ab_variant == "A":
                await self.db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(ab_a_opened=EmailCampaign.ab_a_opened + 1)
                )
            elif recipient.ab_variant == "B":
                await self.db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(ab_b_opened=EmailCampaign.ab_b_opened + 1)
                )

            # Log activity if contact is linked
            if recipient.contact_id:
                try:
                    await log_email_activity(
                        db=self.db,
                        tenant_id=recipient.tenant_id,
                        contact_id=recipient.contact_id,
                        activity_type=EmailActivityType.EMAIL_OPENED,
                        subject="Email geöffnet",
                        campaign_id=recipient.campaign_id,
                        metadata={
                            "ip_address": ip_address,
                            "recipient_id": recipient.id,
                        },
                        commit=False,
                    )
                except Exception as e:
                    logger.warning(f"Activity logging failed for email open: {e}")

            await self.db.flush()
            logger.info("E-Mail geöffnet: {email}", email=recipient.email)

    async def record_click(
        self,
        tracking_token: str,
        url: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        """Record email click event and return original URL."""
        result = await self.db.execute(
            select(EmailRecipient).where(
                EmailRecipient.tracking_token == tracking_token
            )
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            logger.warning("Click tracking: Token nicht gefunden {token}", token=tracking_token)
            return None

        # Record click
        click = EmailClick(
            tenant_id=recipient.tenant_id,
            recipient_id=recipient.id,
            original_url=url,
            clicked_at=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(click)

        # Update recipient status (first click only)
        if not recipient.clicked_at:
            recipient.clicked_at = datetime.utcnow()
            recipient.status = "clicked"

            # Update campaign stats
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(clicked_count=EmailCampaign.clicked_count + 1)
            )

            # Update A/B stats if applicable
            if recipient.ab_variant == "A":
                await self.db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(ab_a_clicked=EmailCampaign.ab_a_clicked + 1)
                )
            elif recipient.ab_variant == "B":
                await self.db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(ab_b_clicked=EmailCampaign.ab_b_clicked + 1)
                )

        # Also record as open if not already
        if not recipient.opened_at:
            recipient.opened_at = datetime.utcnow()
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(opened_count=EmailCampaign.opened_count + 1)
            )

        # Log activity if contact is linked
        if recipient.contact_id:
            try:
                await log_email_activity(
                    db=self.db,
                    tenant_id=recipient.tenant_id,
                    contact_id=recipient.contact_id,
                    activity_type=EmailActivityType.EMAIL_CLICKED,
                    subject=f"Link geklickt: {url[:50]}",
                    campaign_id=recipient.campaign_id,
                    metadata={
                        "url": url,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "recipient_id": recipient.id,
                    },
                    commit=False,
                )
            except Exception as e:
                logger.warning(f"Activity logging failed for email click: {e}")

        await self.db.flush()
        logger.info("E-Mail Link geklickt: {email} -> {url}", email=recipient.email, url=url[:50])

        return url

    async def record_unsubscribe(
        self,
        tracking_token: str,
        ip_address: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Record unsubscribe and return (email, tenant_id) or (None, None)."""
        result = await self.db.execute(
            select(EmailRecipient).where(
                EmailRecipient.tracking_token == tracking_token
            )
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            logger.warning("Unsubscribe: Token nicht gefunden {token}", token=tracking_token)
            return None, None

        # Check if already unsubscribed
        existing = await self.db.execute(
            select(EmailUnsubscribe).where(
                EmailUnsubscribe.tenant_id == recipient.tenant_id,
                EmailUnsubscribe.email == recipient.email,
            )
        )
        if not existing.scalar_one_or_none():
            # Create unsubscribe record
            unsub = EmailUnsubscribe(
                tenant_id=recipient.tenant_id,
                email=recipient.email,
                reason="user_request",
                source_type="campaign",
                source_id=recipient.campaign_id,
                ip_address=ip_address,
            )
            self.db.add(unsub)

            # Update recipient
            recipient.status = "unsubscribed"

            # Update campaign stats
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(unsubscribed_count=EmailCampaign.unsubscribed_count + 1)
            )

            # Log activity if contact is linked
            if recipient.contact_id:
                try:
                    await log_email_activity(
                        db=self.db,
                        tenant_id=recipient.tenant_id,
                        contact_id=recipient.contact_id,
                        activity_type=EmailActivityType.EMAIL_UNSUBSCRIBED,
                        subject="Newsletter abgemeldet",
                        campaign_id=recipient.campaign_id,
                        metadata={
                            "ip_address": ip_address,
                            "recipient_id": recipient.id,
                        },
                        commit=False,
                    )
                except Exception as e:
                    logger.warning(f"Activity logging failed for unsubscribe: {e}")

            await self.db.flush()
            logger.info("Abmeldung: {email}", email=recipient.email)

        return recipient.email, recipient.tenant_id

    async def handle_webhook_event(
        self,
        tenant_id: str,
        event_type: str,
        message_id: str | None,
        email: str | None,
        data: dict,
    ):
        """Handle webhook event from email provider."""
        # Find recipient by message ID or email
        query = select(EmailRecipient).where(EmailRecipient.tenant_id == tenant_id)
        if message_id:
            query = query.where(EmailRecipient.provider_message_id == message_id)
        elif email:
            query = query.where(EmailRecipient.email == email)
        else:
            return

        result = await self.db.execute(query)
        recipient = result.scalar_one_or_none()

        if not recipient:
            return

        now = datetime.utcnow()

        if event_type == "delivered":
            if not recipient.delivered_at:
                recipient.delivered_at = now
                recipient.status = "delivered"
                await self.db.execute(
                    update(EmailCampaign)
                    .where(EmailCampaign.id == recipient.campaign_id)
                    .values(delivered_count=EmailCampaign.delivered_count + 1)
                )

        elif event_type in ("bounce", "bounced"):
            recipient.bounced_at = now
            recipient.status = "bounced"
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(bounced_count=EmailCampaign.bounced_count + 1)
            )

        elif event_type in ("spam", "complained", "spamreport"):
            recipient.status = "spam"
            await self.db.execute(
                update(EmailCampaign)
                .where(EmailCampaign.id == recipient.campaign_id)
                .values(spam_count=EmailCampaign.spam_count + 1)
            )

            # Auto-unsubscribe on spam complaint
            existing = await self.db.execute(
                select(EmailUnsubscribe).where(
                    EmailUnsubscribe.tenant_id == tenant_id,
                    EmailUnsubscribe.email == recipient.email,
                )
            )
            if not existing.scalar_one_or_none():
                unsub = EmailUnsubscribe(
                    tenant_id=tenant_id,
                    email=recipient.email,
                    reason="complaint",
                    source_type="campaign",
                    source_id=recipient.campaign_id,
                )
                self.db.add(unsub)

        # Log activity for contact-relevant events
        if recipient.contact_id and event_type in (
            "delivered", "bounce", "bounced", "spam", "complained", "spamreport"
        ):
            activity_map = {
                "delivered": EmailActivityType.EMAIL_DELIVERED,
                "bounce": EmailActivityType.EMAIL_BOUNCED,
                "bounced": EmailActivityType.EMAIL_BOUNCED,
                "spam": EmailActivityType.EMAIL_COMPLAINED,
                "complained": EmailActivityType.EMAIL_COMPLAINED,
                "spamreport": EmailActivityType.EMAIL_COMPLAINED,
            }
            try:
                await log_email_activity(
                    db=self.db,
                    tenant_id=recipient.tenant_id,
                    contact_id=recipient.contact_id,
                    activity_type=activity_map[event_type],
                    subject=f"Email {event_type}: {recipient.email}",
                    campaign_id=recipient.campaign_id,
                    metadata={"recipient_id": recipient.id, "event_data": data},
                    commit=False,
                )
            except Exception as e:
                logger.warning(f"Activity logging failed for webhook: {e}")

        await self.db.flush()
        logger.info(
            "Webhook Event: {type} für {email}",
            type=event_type,
            email=recipient.email,
        )
