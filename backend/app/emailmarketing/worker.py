"""Email Marketing Background Worker.

Inspired by Listmonk's architecture:
- Polling-based scheduling (every 5 seconds)
- PostgreSQL as queue (no Redis needed)
- Graceful error handling with campaign pause
- Rate limiting per provider
"""

import asyncio
import uuid
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.config import settings
from app.contacts.models import Contact
from app.emailmarketing.models import (
    EmailCampaign,
    EmailProvider,
    EmailRecipient,
    EmailSequence,
    EmailSequenceEnrollment,
    EmailUnsubscribe,
)
from app.emailmarketing.providers import EmailMessage, get_provider
from app.emailmarketing.template_renderer import make_outreach_message_id
from app.emailmarketing.tracking import process_email_content
from app.engagement import (
    EmailActivityType,
    log_email_activity,
)


class EmailWorker:
    """Background worker for email marketing tasks."""

    def __init__(
        self,
        database_url: str | None = None,
        scan_interval: int = 5,
        max_send_errors: int = 10,
        batch_size: int = 100,
    ):
        self.database_url = database_url or settings.database_url
        self.scan_interval = scan_interval
        self.max_send_errors = max_send_errors
        self.batch_size = batch_size
        self.running = False
        self._engine = None
        self._session_factory = None

    async def _get_engine(self):
        """Lazy engine creation."""
        if not self._engine:
            self._engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,
            )
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._engine

    async def _get_session(self) -> AsyncSession:
        """Get a new database session."""
        await self._get_engine()
        return self._session_factory()

    async def run(self):
        """Main loop - runs indefinitely."""
        logger.info("EmailWorker gestartet (Scan-Interval: {interval}s)", interval=self.scan_interval)
        self.running = True

        while self.running:
            try:
                async with await self._get_session() as session:
                    # Process scheduled campaigns
                    await self.process_scheduled_campaigns(session)

                    # Process sequence enrollments
                    await self.process_sequence_enrollments(session)

                    # Reset daily counters if needed
                    await self.reset_daily_counters(session)

                    await session.commit()

            except Exception as e:
                logger.exception("Fehler im Worker-Loop: {err}", err=str(e))

            await asyncio.sleep(self.scan_interval)

        logger.info("EmailWorker gestoppt")

    def stop(self):
        """Stop the worker gracefully."""
        self.running = False

    # ============== Scheduled Campaigns ==============

    async def process_scheduled_campaigns(self, session: AsyncSession):
        """Process campaigns that are scheduled to send now."""
        now = datetime.utcnow()

        # Find scheduled campaigns ready to send
        result = await session.execute(
            select(EmailCampaign)
            .options(selectinload(EmailCampaign.provider))
            .where(
                and_(
                    EmailCampaign.status == "scheduled",
                    EmailCampaign.scheduled_at <= now,
                )
            )
            .order_by(EmailCampaign.scheduled_at.asc())
            .limit(10)
        )
        campaigns = list(result.scalars().all())

        if not campaigns:
            return

        logger.info("Gefunden: {count} geplante Kampagnen", count=len(campaigns))

        for campaign in campaigns:
            try:
                await self._send_campaign(session, campaign)
            except Exception as e:
                logger.exception(
                    "Fehler bei Kampagne {id}: {err}",
                    id=campaign.id,
                    err=str(e),
                )
                await self._handle_campaign_error(session, campaign, str(e))

    async def _send_campaign(self, session: AsyncSession, campaign: EmailCampaign):
        """Send a single campaign."""
        logger.info(
            "Starte Kampagne {id}: {name}",
            id=campaign.id,
            name=campaign.name,
        )

        # Check provider
        if not campaign.provider_id:
            raise ValueError("Kein Provider konfiguriert")

        provider_model = campaign.provider
        if not provider_model or provider_model.status != "active":
            raise ValueError("Provider nicht aktiv")

        # Check rate limit
        if not await self._check_rate_limit(provider_model):
            logger.warning(
                "Rate-Limit erreicht für Provider {id}",
                id=provider_model.id,
            )
            return  # Will retry next scan

        # Update status to sending
        campaign.status = "sending"
        await session.flush()

        # Get or generate recipients
        result = await session.execute(
            select(EmailRecipient).where(
                and_(
                    EmailRecipient.campaign_id == campaign.id,
                    EmailRecipient.status == "pending",
                )
            )
        )
        recipients = list(result.scalars().all())

        if not recipients:
            # Generate recipients from segment/contact_ids
            recipients = await self._generate_recipients(session, campaign)

        if not recipients:
            logger.warning("Keine Empfänger für Kampagne {id}", id=campaign.id)
            campaign.status = "sent"
            campaign.sent_at = datetime.utcnow()
            return

        # Get provider instance
        provider = get_provider(provider_model)

        # Build tracking base URL
        base_tracking_url = settings.api_url or "http://localhost:8002/api/v1"

        # Send emails in batches
        sent_count = 0
        error_count = 0

        for i in range(0, len(recipients), self.batch_size):
            batch = recipients[i : i + self.batch_size]

            # Check rate limit before each batch
            if not await self._check_rate_limit(provider_model):
                logger.info("Rate-Limit erreicht, pausiere Kampagne {id}", id=campaign.id)
                campaign.status = "paused"
                campaign.last_error = "Rate-Limit erreicht"
                return

            for recipient in batch:
                try:
                    # Process content with tracking
                    html = process_email_content(
                        campaign.html_content,
                        recipient.tracking_token,
                        base_tracking_url,
                        recipient.merge_data or {},
                    )

                    # Custom Message-ID for In-Reply-To matching when leads reply
                    outreach_message_id = make_outreach_message_id(
                        prefix="rcpt",
                        ref_id=recipient.id,
                        token=recipient.tracking_token,
                    )
                    message = EmailMessage(
                        to_email=recipient.email,
                        to_name=recipient.name,
                        subject=campaign.subject,
                        html_content=html,
                        text_content=campaign.text_content,
                        tracking_token=recipient.tracking_token,
                        headers={"Message-ID": outreach_message_id},
                    )

                    result = await provider.send_email(message)

                    if result.success:
                        recipient.status = "sent"
                        recipient.sent_at = datetime.utcnow()
                        recipient.provider_message_id = result.message_id
                        recipient.message_id = outreach_message_id
                        sent_count += 1
                        await self._increment_provider_counters(session, provider_model.id)

                        # Log activity if contact is linked
                        if recipient.contact_id:
                            try:
                                await log_email_activity(
                                    db=session,
                                    tenant_id=campaign.tenant_id,
                                    contact_id=recipient.contact_id,
                                    activity_type=EmailActivityType.EMAIL_SENT,
                                    subject=campaign.subject,
                                    campaign_id=campaign.id,
                                    external_id=result.message_id,
                                    metadata={
                                        "campaign_name": campaign.name,
                                        "recipient_id": recipient.id,
                                    },
                                    commit=False,
                                )
                            except Exception as e:
                                logger.warning(f"Activity logging failed for email sent: {e}")
                    else:
                        recipient.status = "bounced"
                        recipient.bounced_at = datetime.utcnow()
                        error_count += 1
                        campaign.bounced_count += 1

                        # Log bounce activity if contact is linked
                        if recipient.contact_id:
                            try:
                                await log_email_activity(
                                    db=session,
                                    tenant_id=campaign.tenant_id,
                                    contact_id=recipient.contact_id,
                                    activity_type=EmailActivityType.EMAIL_BOUNCED,
                                    subject=campaign.subject,
                                    campaign_id=campaign.id,
                                    metadata={
                                        "campaign_name": campaign.name,
                                        "recipient_id": recipient.id,
                                        "error": result.error,
                                    },
                                    commit=False,
                                )
                            except Exception as e:
                                logger.warning(f"Activity logging failed for email bounce: {e}")

                except Exception as e:
                    logger.error(
                        "Fehler beim Senden an {email}: {err}",
                        email=recipient.email,
                        err=str(e),
                    )
                    error_count += 1

                    if error_count >= self.max_send_errors:
                        await self._handle_campaign_error(
                            session, campaign, f"Zu viele Fehler: {error_count}"
                        )
                        return

            await session.flush()

        # Update campaign stats
        campaign.sent_count = sent_count
        campaign.status = "sent"
        campaign.sent_at = datetime.utcnow()

        logger.info(
            "Kampagne {id} abgeschlossen: {sent} gesendet, {errors} Fehler",
            id=campaign.id,
            sent=sent_count,
            errors=error_count,
        )

    async def _generate_recipients(
        self, session: AsyncSession, campaign: EmailCampaign
    ) -> list[EmailRecipient]:
        """Generate recipient list from segment filters or contact IDs."""
        # Build contact query
        query = select(Contact).where(Contact.tenant_id == campaign.tenant_id)

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
        else:
            return []

        result = await session.execute(query)
        contacts = list(result.scalars().all())

        # Get unsubscribed emails
        unsub_result = await session.execute(
            select(EmailUnsubscribe.email).where(
                EmailUnsubscribe.tenant_id == campaign.tenant_id
            )
        )
        unsubscribed = {row[0] for row in unsub_result.all()}

        # Create recipients
        recipients = []
        for contact in contacts:
            if contact.email in unsubscribed:
                continue

            recipient = EmailRecipient(
                tenant_id=campaign.tenant_id,
                campaign_id=campaign.id,
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
            )
            session.add(recipient)
            recipients.append(recipient)

        campaign.total_recipients = len(recipients)
        await session.flush()

        logger.info(
            "Generiert: {count} Empfänger für Kampagne {id}",
            count=len(recipients),
            id=campaign.id,
        )
        return recipients

    async def _handle_campaign_error(
        self, session: AsyncSession, campaign: EmailCampaign, error: str
    ):
        """Handle campaign error - pause after too many errors."""
        campaign.status = "paused"
        campaign.last_error = error
        logger.error("Kampagne {id} pausiert: {err}", id=campaign.id, err=error)

    # ============== Sequence Processing ==============

    async def process_sequence_enrollments(self, session: AsyncSession):
        """Process sequence enrollments that are due."""
        now = datetime.utcnow()

        # Find enrollments ready to send
        result = await session.execute(
            select(EmailSequenceEnrollment)
            .options(
                selectinload(EmailSequenceEnrollment.sequence).selectinload(
                    EmailSequence.steps
                ),
                selectinload(EmailSequenceEnrollment.sequence).selectinload(
                    EmailSequence.provider
                ),
                selectinload(EmailSequenceEnrollment.contact),
            )
            .where(
                and_(
                    EmailSequenceEnrollment.status == "active",
                    EmailSequenceEnrollment.next_send_at <= now,
                )
            )
            .order_by(EmailSequenceEnrollment.next_send_at.asc())
            .limit(50)
        )
        enrollments = list(result.scalars().all())

        if not enrollments:
            return

        logger.info("Gefunden: {count} fällige Sequenz-Enrollments", count=len(enrollments))

        for enrollment in enrollments:
            try:
                # Check if sequence is still active
                if enrollment.sequence.status != "active":
                    enrollment.status = "paused"
                    continue

                await self._process_enrollment_step(session, enrollment)
            except Exception as e:
                logger.exception(
                    "Fehler bei Enrollment {id}: {err}",
                    id=enrollment.id,
                    err=str(e),
                )

    async def _process_enrollment_step(
        self, session: AsyncSession, enrollment: EmailSequenceEnrollment
    ):
        """Process a single enrollment step."""
        sequence = enrollment.sequence
        contact = enrollment.contact

        if not contact or not contact.email:
            enrollment.status = "completed"
            return

        # Get current step
        current_step_num = enrollment.current_step
        steps = sorted(sequence.steps, key=lambda s: s.position)

        if current_step_num >= len(steps):
            # Completed all steps
            enrollment.status = "completed"
            enrollment.completed_at = datetime.utcnow()
            sequence.total_completed += 1
            logger.info(
                "Enrollment {id} abgeschlossen (alle Steps)",
                id=enrollment.id,
            )
            return

        step = steps[current_step_num]

        # Check conditional sending
        if step.send_if_opened_previous is not None:
            # Would need to check previous email open status
            # For now, always send
            pass

        # Get provider
        provider_model = sequence.provider
        if not provider_model or provider_model.status != "active":
            logger.warning("Provider nicht aktiv für Sequenz {id}", id=sequence.id)
            return

        # Check rate limit
        if not await self._check_rate_limit(provider_model):
            return  # Will retry next scan

        # Prepare email
        base_tracking_url = settings.api_url or "http://localhost:8002/api/v1"
        tracking_token = str(uuid.uuid4())

        merge_data = {
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone or "",
            "position": contact.position or "",
        }

        html = process_email_content(
            step.html_content,
            tracking_token,
            base_tracking_url,
            merge_data,
        )

        message = EmailMessage(
            to_email=contact.email,
            to_name=contact.name,
            subject=step.subject,
            html_content=html,
            text_content=step.text_content,
            tracking_token=tracking_token,
        )

        # Send
        provider = get_provider(provider_model)
        result = await provider.send_email(message)

        if result.success:
            # Update enrollment
            enrollment.current_step = current_step_num + 1
            enrollment.last_sent_at = datetime.utcnow()

            # Calculate next send time
            if enrollment.current_step < len(steps):
                next_step = steps[enrollment.current_step]
                delay = timedelta(days=next_step.delay_days, hours=next_step.delay_hours)
                enrollment.next_send_at = datetime.utcnow() + delay

                # Respect send window
                if sequence.send_window_start and sequence.send_window_end:
                    enrollment.next_send_at = self._adjust_to_send_window(
                        enrollment.next_send_at,
                        sequence.send_window_start,
                        sequence.send_window_end,
                        sequence.skip_weekends,
                    )
            else:
                enrollment.status = "completed"
                enrollment.completed_at = datetime.utcnow()
                sequence.total_completed += 1

            # Update step stats
            step.sent_count += 1

            await self._increment_provider_counters(session, provider_model.id)

            # Log activity for sequence email
            if enrollment.contact_id:
                try:
                    await log_email_activity(
                        db=session,
                        tenant_id=sequence.tenant_id,
                        contact_id=enrollment.contact_id,
                        activity_type=EmailActivityType.EMAIL_SENT,
                        subject=step.subject,
                        external_id=result.message_id,
                        metadata={
                            "sequence_id": sequence.id,
                            "sequence_name": sequence.name,
                            "step_position": current_step_num + 1,
                            "enrollment_id": enrollment.id,
                        },
                        commit=False,
                    )
                except Exception as e:
                    logger.warning(f"Activity logging failed for sequence email: {e}")

            logger.info(
                "Sequenz-Step gesendet: Enrollment {eid}, Step {step}",
                eid=enrollment.id,
                step=current_step_num + 1,
            )
        else:
            logger.error(
                "Sequenz-Step fehlgeschlagen: {err}",
                err=result.error,
            )

    def _adjust_to_send_window(
        self,
        dt: datetime,
        window_start: str,
        window_end: str,
        skip_weekends: bool,
    ) -> datetime:
        """Adjust datetime to be within send window."""
        start_hour, start_min = map(int, window_start.split(":"))
        end_hour, end_min = map(int, window_end.split(":"))

        # Check if within window
        current_minutes = dt.hour * 60 + dt.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        if current_minutes < start_minutes:
            # Before window - set to start
            dt = dt.replace(hour=start_hour, minute=start_min)
        elif current_minutes > end_minutes:
            # After window - set to next day start
            dt = dt + timedelta(days=1)
            dt = dt.replace(hour=start_hour, minute=start_min)

        # Skip weekends
        if skip_weekends:
            while dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
                dt = dt + timedelta(days=1)

        return dt

    # ============== Rate Limiting ==============

    async def _check_rate_limit(self, provider: EmailProvider) -> bool:
        """Check if provider is within rate limits."""
        return (
            provider.emails_sent_hour < provider.hourly_limit
            and provider.emails_sent_today < provider.daily_limit
        )

    async def _increment_provider_counters(self, session: AsyncSession, provider_id: int):
        """Atomically increment provider counters."""
        await session.execute(
            update(EmailProvider)
            .where(EmailProvider.id == provider_id)
            .values(
                emails_sent_hour=EmailProvider.emails_sent_hour + 1,
                emails_sent_today=EmailProvider.emails_sent_today + 1,
            )
        )

    # ============== Counter Reset ==============

    async def reset_daily_counters(self, session: AsyncSession):
        """Reset daily counters at midnight."""
        now = datetime.utcnow()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Reset providers that haven't been reset today
        await session.execute(
            update(EmailProvider)
            .where(
                (EmailProvider.last_reset_at < midnight)
                | (EmailProvider.last_reset_at.is_(None))
            )
            .values(
                emails_sent_today=0,
                emails_sent_hour=0,
                last_reset_at=now,
            )
        )

    # ============== Hourly Counter Reset ==============

    async def reset_hourly_counters(self, session: AsyncSession):
        """Reset hourly counters every hour."""
        # This could be enhanced with a separate last_hourly_reset field
        # For now, we reset hourly counter more frequently
        await session.execute(
            update(EmailProvider)
            .where(EmailProvider.emails_sent_hour > 0)
            .values(emails_sent_hour=0)
        )


async def run_worker():
    """Entry point for running the worker."""
    worker = EmailWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
