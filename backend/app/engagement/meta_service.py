"""
Meta Conversions API Service

Server-side event tracking to Meta (Facebook) Conversions API.
Sends hashed user data for attribution and ad optimization.

Documentation:
    https://developers.facebook.com/docs/marketing-api/conversions-api

Usage:
    service = MetaConversionsService(db, tenant_id)
    await service.track_page_view(contact, url="https://example.com/product")
    await service.track_lead(contact, pipeline_name="Solar KMU")
    await service.track_conversion(contact, value=5000.0, currency="EUR")
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Contact
from app.engagement.meta_models import ConversionEvent, MetaEventName, MetaIntegration


class MetaConversionsService:
    """
    Service for sending conversion events to Meta Conversions API.

    The Conversions API (CAPI) allows server-to-server event tracking,
    independent of browser cookies or ad blockers. Events are sent with
    hashed PII (email, phone, name) for user matching.

    Attributes:
        db: Database session
        tenant_id: Current tenant ID
        integration: Cached MetaIntegration instance
    """

    # Meta Graph API base URL
    GRAPH_API_VERSION = "v18.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    # Test event code for debugging (shows in Events Manager Test Events)
    TEST_EVENT_CODE = "TEST12345"

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize the service.

        Args:
            db: Async database session
            tenant_id: Current tenant identifier
        """
        self.db = db
        self.tenant_id = tenant_id
        self._integration: MetaIntegration | None = None

    # ============== Integration Management ==============

    async def get_integration(self) -> MetaIntegration | None:
        """
        Get the Meta integration for current tenant.

        Returns:
            MetaIntegration instance or None if not configured
        """
        if self._integration is not None:
            return self._integration

        result = await self.db.execute(
            select(MetaIntegration).where(
                MetaIntegration.tenant_id == self.tenant_id,
                MetaIntegration.is_active == True,  # noqa: E712
            )
        )
        self._integration = result.scalar_one_or_none()
        return self._integration

    async def create_integration(
        self,
        pixel_id: str,
        access_token: str,
        ad_account_id: str | None = None,
        test_mode: bool = False,
    ) -> MetaIntegration:
        """
        Create or update Meta integration for tenant.

        Args:
            pixel_id: Meta Pixel ID from Events Manager
            access_token: System User access token
            ad_account_id: Optional Ad Account ID for Custom Audiences
            test_mode: If True, events are marked as test

        Returns:
            Created or updated MetaIntegration

        Raises:
            ValueError: If pixel_id or access_token is invalid
        """
        # Validate pixel_id format (numeric, 15-16 digits)
        if not re.match(r"^\d{15,16}$", pixel_id):
            raise ValueError("Pixel ID must be 15-16 digits")

        # Check if integration exists
        existing = await self.db.execute(
            select(MetaIntegration).where(MetaIntegration.tenant_id == self.tenant_id)
        )
        integration = existing.scalar_one_or_none()

        if integration:
            # Update existing
            integration.pixel_id = pixel_id
            integration.access_token = access_token
            integration.ad_account_id = ad_account_id
            integration.test_mode = test_mode
            integration.is_active = True
            integration.updated_at = datetime.utcnow()
        else:
            # Create new
            integration = MetaIntegration(
                tenant_id=self.tenant_id,
                pixel_id=pixel_id,
                access_token=access_token,
                ad_account_id=ad_account_id,
                test_mode=test_mode,
                is_active=True,
            )
            self.db.add(integration)

        await self.db.commit()
        await self.db.refresh(integration)

        self._integration = integration
        logger.info(f"Meta integration configured for tenant {self.tenant_id}")
        return integration

    async def update_integration(
        self,
        pixel_id: str | None = None,
        access_token: str | None = None,
        ad_account_id: str | None = None,
        is_active: bool | None = None,
        test_mode: bool | None = None,
    ) -> MetaIntegration:
        """
        Update existing Meta integration.

        Args:
            pixel_id: New Pixel ID (optional)
            access_token: New access token (optional)
            ad_account_id: New Ad Account ID (optional)
            is_active: Enable/disable integration (optional)
            test_mode: Enable/disable test mode (optional)

        Returns:
            Updated MetaIntegration

        Raises:
            ValueError: If no integration exists
        """
        integration = await self.get_integration()
        if not integration:
            # Try to get inactive integration
            result = await self.db.execute(
                select(MetaIntegration).where(MetaIntegration.tenant_id == self.tenant_id)
            )
            integration = result.scalar_one_or_none()
            if not integration:
                raise ValueError("No Meta integration configured")

        if pixel_id is not None:
            if not re.match(r"^\d{15,16}$", pixel_id):
                raise ValueError("Pixel ID must be 15-16 digits")
            integration.pixel_id = pixel_id

        if access_token is not None:
            integration.access_token = access_token

        if ad_account_id is not None:
            integration.ad_account_id = ad_account_id

        if is_active is not None:
            integration.is_active = is_active

        if test_mode is not None:
            integration.test_mode = test_mode

        integration.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(integration)

        self._integration = integration if integration.is_active else None
        return integration

    async def delete_integration(self) -> bool:
        """
        Deactivate Meta integration (soft delete).

        Returns:
            True if integration was deactivated
        """
        integration = await self.get_integration()
        if not integration:
            return False

        integration.is_active = False
        integration.updated_at = datetime.utcnow()
        await self.db.commit()

        self._integration = None
        logger.info(f"Meta integration deactivated for tenant {self.tenant_id}")
        return True

    # ============== PII Hashing ==============

    def hash_pii(self, value: str | None) -> str | None:
        """
        Hash PII value according to Meta specification.

        Meta requires SHA256 hashing of lowercase, trimmed values.
        Empty or None values return None.

        Args:
            value: Raw PII value (email, phone, name)

        Returns:
            SHA256 hash as hex string, or None
        """
        if not value:
            return None

        # Lowercase and trim whitespace
        normalized = value.lower().strip()
        if not normalized:
            return None

        # SHA256 hash
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def normalize_phone(self, phone: str | None) -> str | None:
        """
        Normalize phone number for hashing.

        Meta expects phone numbers as digits only, including country code.
        Example: +49 123 456789 -> 49123456789

        Args:
            phone: Raw phone number

        Returns:
            Normalized phone number (digits only)
        """
        if not phone:
            return None

        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone)

        # Add country code if missing (assume Germany)
        if digits.startswith("0"):
            digits = "49" + digits[1:]

        return digits if digits else None

    def build_user_data(self, contact: Contact) -> dict[str, list[str]]:
        """
        Build hashed user_data payload from contact.

        Meta accepts multiple values per field as arrays.
        Only non-empty hashed values are included.

        Args:
            contact: Contact model instance

        Returns:
            Dict with hashed PII fields (em, ph, fn, ln, etc.)
        """
        user_data = {}

        # Email (em)
        if email_hash := self.hash_pii(contact.email):
            user_data["em"] = [email_hash]

        # Phone (ph) - normalized before hashing
        if contact.phone:
            normalized = self.normalize_phone(contact.phone)
            if phone_hash := self.hash_pii(normalized):
                user_data["ph"] = [phone_hash]

        # First name (fn)
        if fn_hash := self.hash_pii(contact.first_name):
            user_data["fn"] = [fn_hash]

        # Last name (ln)
        if ln_hash := self.hash_pii(contact.last_name):
            user_data["ln"] = [ln_hash]

        # External ID (external_id) - use contact ID
        user_data["external_id"] = [str(contact.id)]

        return user_data

    def get_user_data_fields(self, user_data: dict) -> list[str]:
        """
        Get list of field names that were populated.

        Used for logging which PII fields were sent (without the actual data).

        Args:
            user_data: Built user_data dict

        Returns:
            List of field names (e.g., ["em", "ph", "fn"])
        """
        return [k for k, v in user_data.items() if v]

    # ============== Event Sending ==============

    async def send_event(
        self,
        event_name: str,
        contact: Contact,
        event_source_url: str | None = None,
        custom_data: dict | None = None,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> str | None:
        """
        Send a conversion event to Meta Conversions API.

        This is the core method that handles:
        - Building the event payload with hashed user data
        - Sending to Meta Graph API
        - Logging the event to database
        - Updating integration statistics

        Args:
            event_name: Standard Meta event name (PageView, Lead, Purchase, etc.)
            contact: Contact model with PII for matching
            event_source_url: URL where the event occurred (for PageView)
            custom_data: Event-specific data (value, currency, content_name, etc.)
            pipeline_id: Optional associated pipeline
            enrollment_id: Optional associated enrollment

        Returns:
            Event ID if successful, None if failed

        Raises:
            ValueError: If no integration is configured
        """
        integration = await self.get_integration()
        if not integration:
            logger.warning(f"No Meta integration for tenant {self.tenant_id}")
            return None

        # Build event payload
        event_time = datetime.utcnow()
        event_id = self._generate_event_id(contact.id, event_name, event_time)

        user_data = self.build_user_data(contact)
        user_data_fields = self.get_user_data_fields(user_data)

        event = {
            "event_name": event_name,
            "event_time": int(event_time.timestamp()),
            "event_id": event_id,
            "action_source": "system_generated",
            "user_data": user_data,
        }

        if event_source_url:
            event["event_source_url"] = event_source_url

        if custom_data:
            event["custom_data"] = custom_data

        # Prepare request payload
        payload = {
            "data": [event],
            "access_token": integration.access_token,
        }

        # Add test event code if in test mode
        if integration.test_mode:
            payload["test_event_code"] = self.TEST_EVENT_CODE

        # Create event log entry
        event_log = ConversionEvent(
            tenant_id=self.tenant_id,
            meta_integration_id=integration.id,
            event_name=event_name,
            event_time=event_time,
            event_id=event_id,
            contact_id=contact.id,
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
            user_data_fields=user_data_fields,
            custom_data=custom_data,
            status="pending",
        )
        self.db.add(event_log)
        await self.db.flush()

        # Send to Meta
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.GRAPH_API_BASE}/{integration.pixel_id}/events",
                    json=payload,
                )

                event_log.response_code = response.status_code
                event_log.sent_at = datetime.utcnow()

                if response.status_code == 200:
                    response_data = response.json()
                    event_log.response_body = response_data
                    event_log.status = "test" if integration.test_mode else "sent"

                    # Update integration stats
                    integration.last_event_at = datetime.utcnow()
                    integration.total_events_sent += 1

                    logger.info(
                        f"Meta CAPI: Sent {event_name} for contact {contact.id}"
                    )
                else:
                    error_data = response.json() if response.content else {}
                    event_log.response_body = error_data
                    event_log.status = "failed"
                    event_log.error_message = error_data.get("error", {}).get(
                        "message", f"HTTP {response.status_code}"
                    )

                    # Update integration stats
                    integration.total_events_failed += 1

                    logger.error(
                        f"Meta CAPI error: {event_log.error_message} "
                        f"(contact={contact.id}, event={event_name})"
                    )

        except httpx.RequestError as e:
            event_log.status = "failed"
            event_log.error_message = str(e)
            integration.total_events_failed += 1
            logger.exception(f"Meta CAPI request failed: {e}")

        await self.db.commit()
        return event_id if event_log.status in ("sent", "test") else None

    def _generate_event_id(
        self, contact_id: int, event_name: str, event_time: datetime
    ) -> str:
        """
        Generate unique event ID for deduplication.

        Meta uses event_id to deduplicate events from browser pixel
        and Conversions API. Format: contact_event_timestamp

        Args:
            contact_id: Contact ID
            event_name: Event name
            event_time: Event timestamp

        Returns:
            Unique event ID string
        """
        timestamp = int(event_time.timestamp())
        return f"{contact_id}_{event_name}_{timestamp}"

    # ============== Convenience Methods ==============

    async def track_page_view(
        self,
        contact: Contact,
        url: str,
        pipeline_id: int | None = None,
    ) -> str | None:
        """
        Track a page view event.

        Typically triggered when a contact clicks a tracking link.

        Args:
            contact: Contact who viewed the page
            url: URL of the viewed page
            pipeline_id: Optional associated pipeline

        Returns:
            Event ID if successful
        """
        return await self.send_event(
            event_name=MetaEventName.PAGE_VIEW,
            contact=contact,
            event_source_url=url,
            pipeline_id=pipeline_id,
        )

    async def track_lead(
        self,
        contact: Contact,
        pipeline_name: str,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> str | None:
        """
        Track a lead event (pipeline enrollment).

        Triggered when a contact is enrolled in an engagement pipeline.

        Args:
            contact: Contact who became a lead
            pipeline_name: Name of the pipeline
            pipeline_id: Pipeline ID
            enrollment_id: Enrollment ID

        Returns:
            Event ID if successful
        """
        return await self.send_event(
            event_name=MetaEventName.LEAD,
            contact=contact,
            custom_data={"content_name": pipeline_name},
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
        )

    async def track_contact(
        self,
        contact: Contact,
        channel: str,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> str | None:
        """
        Track a contact event (first response from contact).

        Triggered when a contact responds to outreach for the first time.

        Args:
            contact: Contact who responded
            channel: Channel of response (email, linkedin, whatsapp)
            pipeline_id: Pipeline ID
            enrollment_id: Enrollment ID

        Returns:
            Event ID if successful
        """
        return await self.send_event(
            event_name=MetaEventName.CONTACT,
            contact=contact,
            custom_data={"content_category": channel},
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
        )

    async def track_conversion(
        self,
        contact: Contact,
        value: float | None = None,
        currency: str = "EUR",
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> str | None:
        """
        Track a conversion (purchase) event.

        Triggered when a deal is won / enrollment completed successfully.

        Args:
            contact: Contact who converted
            value: Conversion value (deal amount)
            currency: Currency code (default EUR)
            pipeline_id: Pipeline ID
            enrollment_id: Enrollment ID

        Returns:
            Event ID if successful
        """
        custom_data = {}
        if value is not None:
            custom_data["value"] = value
            custom_data["currency"] = currency

        return await self.send_event(
            event_name=MetaEventName.PURCHASE,
            contact=contact,
            custom_data=custom_data if custom_data else None,
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
        )

    async def track_schedule(
        self,
        contact: Contact,
        appointment_type: str | None = None,
        pipeline_id: int | None = None,
        enrollment_id: int | None = None,
    ) -> str | None:
        """
        Track a schedule event (appointment booked).

        Triggered when a contact books a meeting or demo.

        Args:
            contact: Contact who scheduled
            appointment_type: Type of appointment (demo, consultation, etc.)
            pipeline_id: Pipeline ID
            enrollment_id: Enrollment ID

        Returns:
            Event ID if successful
        """
        custom_data = {}
        if appointment_type:
            custom_data["content_name"] = appointment_type

        return await self.send_event(
            event_name=MetaEventName.SCHEDULE,
            contact=contact,
            custom_data=custom_data if custom_data else None,
            pipeline_id=pipeline_id,
            enrollment_id=enrollment_id,
        )

    # ============== Event Retrieval ==============

    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        event_name: str | None = None,
        contact_id: int | None = None,
        days: int | None = None,
    ) -> tuple[list[ConversionEvent], int]:
        """
        Get conversion events with filtering.

        Args:
            limit: Maximum number of events to return
            offset: Number of events to skip
            status: Filter by status (sent, failed, test)
            event_name: Filter by event name
            contact_id: Filter by contact
            days: Filter to last N days

        Returns:
            Tuple of (events list, total count)
        """
        query = select(ConversionEvent).where(
            ConversionEvent.tenant_id == self.tenant_id
        )

        if status:
            query = query.where(ConversionEvent.status == status)
        if event_name:
            query = query.where(ConversionEvent.event_name == event_name)
        if contact_id:
            query = query.where(ConversionEvent.contact_id == contact_id)
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(ConversionEvent.event_time >= cutoff)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch with pagination
        query = query.order_by(ConversionEvent.event_time.desc())
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        events = list(result.scalars().all())

        return events, total

    async def get_stats(self, days: int = 7) -> dict[str, Any]:
        """
        Get event statistics for the specified period.

        Args:
            days: Number of days to include (default 7)

        Returns:
            Statistics dict with totals, success rate, and daily breakdown
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Base query
        base_query = select(ConversionEvent).where(
            ConversionEvent.tenant_id == self.tenant_id,
            ConversionEvent.event_time >= cutoff,
        )

        # Total events
        total_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = total_result.scalar() or 0

        # Events by status
        status_query = select(
            ConversionEvent.status, func.count().label("count")
        ).where(
            ConversionEvent.tenant_id == self.tenant_id,
            ConversionEvent.event_time >= cutoff,
        ).group_by(ConversionEvent.status)

        status_result = await self.db.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}

        sent = status_counts.get("sent", 0) + status_counts.get("test", 0)
        failed = status_counts.get("failed", 0)

        # Events by type
        type_query = select(
            ConversionEvent.event_name, func.count().label("count")
        ).where(
            ConversionEvent.tenant_id == self.tenant_id,
            ConversionEvent.event_time >= cutoff,
        ).group_by(ConversionEvent.event_name)

        type_result = await self.db.execute(type_query)
        events_by_type = {row.event_name: row.count for row in type_result}

        # Events by day
        daily_query = select(
            func.date(ConversionEvent.event_time).label("date"),
            func.count().label("total"),
            func.count().filter(
                ConversionEvent.status.in_(["sent", "test"])
            ).label("sent"),
            func.count().filter(ConversionEvent.status == "failed").label("failed"),
        ).where(
            ConversionEvent.tenant_id == self.tenant_id,
            ConversionEvent.event_time >= cutoff,
        ).group_by(
            func.date(ConversionEvent.event_time)
        ).order_by(
            func.date(ConversionEvent.event_time)
        )

        daily_result = await self.db.execute(daily_query)
        events_by_day = [
            {
                "date": str(row.date),
                "count": row.total,
                "sent": row.sent,
                "failed": row.failed,
            }
            for row in daily_result
        ]

        return {
            "period_start": cutoff.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_events": total,
            "events_sent": sent,
            "events_failed": failed,
            "success_rate": (sent / total * 100) if total > 0 else 100.0,
            "events_by_type": events_by_type,
            "events_by_day": events_by_day,
        }

    # ============== Test Event ==============

    async def send_test_event(
        self,
        event_name: str = MetaEventName.PAGE_VIEW,
        contact_id: int | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a test event to verify integration.

        Uses test mode regardless of integration setting.
        If no contact specified, creates a dummy event.

        Args:
            event_name: Event type to test
            contact_id: Optional contact to use
            url: Optional URL for PageView events

        Returns:
            Dict with success status and response details
        """
        integration = await self.get_integration()
        if not integration:
            return {
                "success": False,
                "message": "Meta integration not configured",
            }

        # Get or create dummy contact
        contact = None
        if contact_id:
            result = await self.db.execute(
                select(Contact).where(Contact.id == contact_id)
            )
            contact = result.scalar_one_or_none()

        if not contact:
            # Create dummy data for test
            class DummyContact:
                id = 0
                email = "test@example.com"
                phone = "+49123456789"
                first_name = "Test"
                last_name = "User"

            contact = DummyContact()

        # Force test mode for this event
        original_test_mode = integration.test_mode
        integration.test_mode = True

        try:
            event_id = await self.send_event(
                event_name=event_name,
                contact=contact,
                event_source_url=url or "https://test.example.com",
                custom_data={"test": True},
            )

            # Get the event log
            result = await self.db.execute(
                select(ConversionEvent).where(ConversionEvent.event_id == event_id)
            )
            event_log = result.scalar_one_or_none()

            if event_log and event_log.status == "test":
                return {
                    "success": True,
                    "event_id": event_id,
                    "message": "Test-Event erfolgreich gesendet",
                    "response_body": event_log.response_body,
                }
            else:
                return {
                    "success": False,
                    "event_id": event_id,
                    "message": event_log.error_message if event_log else "Unknown error",
                    "response_body": event_log.response_body if event_log else None,
                }

        finally:
            # Restore original test mode
            integration.test_mode = original_test_mode
            await self.db.commit()
