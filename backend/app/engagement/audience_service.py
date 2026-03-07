"""
Custom Audience Service

Manages Meta Custom Audiences for retargeting.
Syncs contact segments to Meta ad accounts.

Documentation:
    https://developers.facebook.com/docs/marketing-api/audiences/guides/custom-audiences

Usage:
    service = CustomAudienceService(db, tenant_id)
    audience = await service.create_audience("Solar Leads", pipeline_id=1, stages=["engaged"])
    await service.sync_audience(audience.id)
"""

import hashlib
from datetime import UTC, datetime

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.engagement.meta_models import (
    AudienceSyncLog,
    CustomAudience,
    MetaIntegration,
    SyncMode,
)
from app.engagement.models import PipelineEnrollment


class CustomAudienceService:
    """
    Service for managing Meta Custom Audiences.

    Handles audience creation, user sync, and statistics.
    All PII is hashed before sending to Meta.

    Attributes:
        GRAPH_API_VERSION: Meta Graph API version
        BATCH_SIZE: Max users per API request
    """

    GRAPH_API_VERSION = "v18.0"
    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    BATCH_SIZE = 10000  # Meta allows up to 10,000 users per request

    def __init__(self, db: AsyncSession, tenant_id: str):
        """
        Initialize service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = tenant_id

    # ============== PII Hashing ==============

    def hash_pii(self, value: str | None) -> str:
        """
        Hash PII value according to Meta specification.

        Meta requires:
        - Lowercase
        - Trim whitespace
        - SHA256 hash

        Args:
            value: Raw PII value

        Returns:
            Hashed value or empty string if None
        """
        if not value or not value.strip():
            return ""
        return hashlib.sha256(value.lower().strip().encode()).hexdigest()

    def normalize_phone(self, phone: str | None) -> str:
        """
        Normalize phone number for hashing.

        Removes all non-digit characters.
        For German numbers starting with 0, replaces with 49.

        Args:
            phone: Raw phone number

        Returns:
            Normalized phone or empty string
        """
        if not phone:
            return ""
        # Remove all non-digits
        digits = "".join(c for c in phone if c.isdigit())
        # German numbers: 0xxx -> 49xxx
        if digits.startswith("0") and not digits.startswith("00"):
            digits = "49" + digits[1:]
        return digits

    def hash_contact(self, contact: Contact) -> list[str]:
        """
        Create hashed data row for a contact.

        Schema: [EMAIL, PHONE, FN, LN]

        Args:
            contact: Contact to hash

        Returns:
            List of hashed values
        """
        return [
            self.hash_pii(contact.email) if contact.email else "",
            self.hash_pii(self.normalize_phone(contact.phone)) if contact.phone else "",
            self.hash_pii(contact.first_name) if contact.first_name else "",
            self.hash_pii(contact.last_name) if contact.last_name else "",
        ]

    def is_valid_contact_data(self, hashed_row: list[str]) -> bool:
        """
        Check if contact has enough data for matching.

        Meta requires at least email or phone.

        Args:
            hashed_row: Hashed contact data

        Returns:
            True if valid for sync
        """
        # Need at least email or phone
        return bool(hashed_row[0] or hashed_row[1])

    # ============== Integration Access ==============

    async def get_integration(self) -> MetaIntegration | None:
        """
        Get active Meta integration for tenant.

        Returns:
            MetaIntegration or None
        """
        result = await self.db.execute(
            select(MetaIntegration).where(
                MetaIntegration.tenant_id == self.tenant_id,
                MetaIntegration.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def require_integration(self) -> MetaIntegration:
        """
        Get integration or raise error.

        Returns:
            MetaIntegration

        Raises:
            ValueError: If no integration configured
        """
        integration = await self.get_integration()
        if not integration:
            raise ValueError("Meta integration not configured")
        if not integration.ad_account_id:
            raise ValueError("Ad Account ID not configured for Custom Audiences")
        return integration

    # ============== Audience CRUD ==============

    async def create_audience(
        self,
        name: str,
        description: str | None = None,
        pipeline_id: int | None = None,
        segment_filter: dict | None = None,
        sync_mode: str = SyncMode.MANUAL,
        create_in_meta: bool = True,
    ) -> CustomAudience:
        """
        Create a new Custom Audience.

        Args:
            name: Audience display name
            description: Optional description
            pipeline_id: Filter to specific pipeline
            segment_filter: JSON filter (stages, tags, etc.)
            sync_mode: manual, daily, or realtime
            create_in_meta: Whether to create in Meta immediately

        Returns:
            Created CustomAudience

        Raises:
            ValueError: If integration not configured
        """
        integration = await self.require_integration()

        audience = CustomAudience(
            tenant_id=self.tenant_id,
            meta_integration_id=integration.id,
            name=name,
            description=description,
            pipeline_id=pipeline_id,
            segment_filter=segment_filter or {},
            sync_mode=sync_mode,
            is_active=True,
        )
        self.db.add(audience)
        await self.db.flush()

        if create_in_meta:
            try:
                meta_audience_id = await self._create_meta_audience(
                    integration, name, description
                )
                audience.meta_audience_id = meta_audience_id
                audience.meta_audience_name = name
            except Exception as e:
                logger.error(f"Failed to create Meta audience: {e}")
                # Still save the local audience, can retry Meta creation later

        await self.db.commit()
        await self.db.refresh(audience)

        logger.info(f"Created Custom Audience: {name} (id={audience.id})")
        return audience

    async def get_audience(self, audience_id: int) -> CustomAudience | None:
        """
        Get audience by ID.

        Args:
            audience_id: Audience ID

        Returns:
            CustomAudience or None
        """
        result = await self.db.execute(
            select(CustomAudience)
            .options(selectinload(CustomAudience.pipeline))
            .where(
                CustomAudience.id == audience_id,
                CustomAudience.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_audiences(
        self,
        pipeline_id: int | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CustomAudience], int]:
        """
        List Custom Audiences with optional filters.

        Args:
            pipeline_id: Filter by pipeline
            is_active: Filter by active status
            limit: Max results
            offset: Skip count

        Returns:
            Tuple of (audiences, total_count)
        """
        query = select(CustomAudience).where(CustomAudience.tenant_id == self.tenant_id)

        if pipeline_id is not None:
            query = query.where(CustomAudience.pipeline_id == pipeline_id)
        if is_active is not None:
            query = query.where(CustomAudience.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.options(selectinload(CustomAudience.pipeline))
        query = query.order_by(CustomAudience.name)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        audiences = list(result.scalars().all())

        return audiences, total

    async def update_audience(
        self,
        audience_id: int,
        name: str | None = None,
        description: str | None = None,
        segment_filter: dict | None = None,
        sync_mode: str | None = None,
        is_active: bool | None = None,
    ) -> CustomAudience:
        """
        Update audience configuration.

        Args:
            audience_id: Audience to update
            name: New name
            description: New description
            segment_filter: New filter
            sync_mode: New sync mode
            is_active: New active status

        Returns:
            Updated CustomAudience

        Raises:
            ValueError: If audience not found
        """
        audience = await self.get_audience(audience_id)
        if not audience:
            raise ValueError(f"Audience {audience_id} not found")

        if name is not None:
            audience.name = name
        if description is not None:
            audience.description = description
        if segment_filter is not None:
            audience.segment_filter = segment_filter
        if sync_mode is not None:
            audience.sync_mode = sync_mode
        if is_active is not None:
            audience.is_active = is_active

        await self.db.commit()
        await self.db.refresh(audience)

        logger.info(f"Updated Custom Audience: {audience.name}")
        return audience

    async def delete_audience(self, audience_id: int, delete_in_meta: bool = False) -> None:
        """
        Delete audience.

        Args:
            audience_id: Audience to delete
            delete_in_meta: Whether to delete in Meta (default: False)

        Raises:
            ValueError: If audience not found
        """
        audience = await self.get_audience(audience_id)
        if not audience:
            raise ValueError(f"Audience {audience_id} not found")

        if delete_in_meta and audience.meta_audience_id:
            try:
                integration = await self.require_integration()
                await self._delete_meta_audience(integration, audience.meta_audience_id)
            except Exception as e:
                logger.warning(f"Failed to delete Meta audience: {e}")

        await self.db.delete(audience)
        await self.db.commit()

        logger.info(f"Deleted Custom Audience: {audience.name}")

    # ============== Contact Fetching ==============

    async def get_contacts_for_audience(self, audience: CustomAudience) -> list[Contact]:
        """
        Get contacts matching audience segment filter.

        Args:
            audience: Audience with filter config

        Returns:
            List of matching contacts
        """
        query = select(Contact).where(Contact.tenant_id == self.tenant_id)

        # Filter by pipeline enrollments if pipeline specified
        if audience.pipeline_id:
            enrollment_query = select(PipelineEnrollment.contact_id).where(
                PipelineEnrollment.pipeline_id == audience.pipeline_id,
                PipelineEnrollment.tenant_id == self.tenant_id,
            )

            # Stage filter
            stages = audience.segment_filter.get("stages", [])
            if stages:
                enrollment_query = enrollment_query.where(
                    PipelineEnrollment.stage.in_(stages)
                )

            # Status filter
            statuses = audience.segment_filter.get("statuses", [])
            if statuses:
                enrollment_query = enrollment_query.where(
                    PipelineEnrollment.status.in_(statuses)
                )

            query = query.where(Contact.id.in_(enrollment_query))

        # Tag filter
        tags = audience.segment_filter.get("tags", [])
        if tags:
            # Assuming Contact has a tags JSONB column
            for tag in tags:
                query = query.where(Contact.tags.contains([tag]))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ============== Sync Operations ==============

    async def sync_audience(self, audience_id: int) -> AudienceSyncLog:
        """
        Sync contacts to Meta Custom Audience.

        Fetches matching contacts, hashes PII, and sends to Meta.

        Args:
            audience_id: Audience to sync

        Returns:
            AudienceSyncLog with results

        Raises:
            ValueError: If audience not found
        """
        audience = await self.get_audience(audience_id)
        if not audience:
            raise ValueError(f"Audience {audience_id} not found")

        integration = await self.require_integration()

        # Create sync log
        sync_log = AudienceSyncLog(
            tenant_id=self.tenant_id,
            audience_id=audience_id,
            operation="replace",
            status="pending",
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # Get matching contacts
            contacts = await self.get_contacts_for_audience(audience)
            sync_log.contacts_processed = len(contacts)

            if not contacts:
                sync_log.status = "success"
                sync_log.completed_at = datetime.now(UTC)
                audience.last_sync_at = datetime.now(UTC)
                audience.last_sync_count = 0
                audience.last_sync_status = "success"
                await self.db.commit()
                return sync_log

            # Create audience in Meta if not exists
            if not audience.meta_audience_id:
                audience.meta_audience_id = await self._create_meta_audience(
                    integration, audience.name, audience.description
                )

            # Hash and filter contacts
            hashed_data = []
            for contact in contacts:
                hashed_row = self.hash_contact(contact)
                if self.is_valid_contact_data(hashed_row):
                    hashed_data.append(hashed_row)

            # Send to Meta in batches
            total_added = 0
            for i in range(0, len(hashed_data), self.BATCH_SIZE):
                batch = hashed_data[i : i + self.BATCH_SIZE]
                added = await self._add_users_to_audience(
                    integration, audience.meta_audience_id, batch
                )
                total_added += added

            sync_log.contacts_added = total_added
            sync_log.status = "success"
            sync_log.completed_at = datetime.now(UTC)

            # Update audience stats
            audience.audience_size = total_added
            audience.last_sync_at = datetime.now(UTC)
            audience.last_sync_count = total_added
            audience.last_sync_status = "success"

            await self.db.commit()

            logger.info(
                f"Synced {total_added} contacts to audience {audience.name}"
            )

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now(UTC)

            audience.last_sync_at = datetime.now(UTC)
            audience.last_sync_status = "failed"

            await self.db.commit()

            logger.error(f"Audience sync failed: {e}")
            raise

        return sync_log

    async def add_contact_to_audience(
        self, audience_id: int, contact_id: int
    ) -> bool:
        """
        Add single contact to audience (for realtime sync).

        Args:
            audience_id: Target audience
            contact_id: Contact to add

        Returns:
            True if successful
        """
        audience = await self.get_audience(audience_id)
        if not audience or not audience.meta_audience_id:
            return False

        integration = await self.get_integration()
        if not integration:
            return False

        # Get contact
        result = await self.db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            return False

        # Hash and validate
        hashed_row = self.hash_contact(contact)
        if not self.is_valid_contact_data(hashed_row):
            return False

        try:
            await self._add_users_to_audience(
                integration, audience.meta_audience_id, [hashed_row]
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to add contact to audience: {e}")
            return False

    # ============== Sync Logs ==============

    async def get_sync_logs(
        self,
        audience_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AudienceSyncLog], int]:
        """
        Get sync logs with optional audience filter.

        Args:
            audience_id: Filter by audience
            limit: Max results
            offset: Skip count

        Returns:
            Tuple of (logs, total_count)
        """
        query = select(AudienceSyncLog).where(
            AudienceSyncLog.tenant_id == self.tenant_id
        )

        if audience_id is not None:
            query = query.where(AudienceSyncLog.audience_id == audience_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(AudienceSyncLog.started_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    # ============== Meta API Calls ==============

    async def _create_meta_audience(
        self,
        integration: MetaIntegration,
        name: str,
        description: str | None = None,
    ) -> str:
        """
        Create Custom Audience in Meta.

        Args:
            integration: Meta integration with credentials
            name: Audience name
            description: Optional description

        Returns:
            Meta audience ID

        Raises:
            Exception: If API call fails
        """
        url = f"{self.GRAPH_API_BASE}/act_{integration.ad_account_id}/customaudiences"

        payload = {
            "name": name,
            "description": description or f"go4-automate: {name}",
            "subtype": "CUSTOM",
            "customer_file_source": "USER_PROVIDED_ONLY",
            "access_token": integration.access_token,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, data=payload)

            if response.status_code != 200:
                error = response.json().get("error", {})
                raise Exception(f"Meta API error: {error.get('message', response.text)}")

            data = response.json()
            return data["id"]

    async def _add_users_to_audience(
        self,
        integration: MetaIntegration,
        audience_id: str,
        hashed_data: list[list[str]],
    ) -> int:
        """
        Add users to Custom Audience.

        Args:
            integration: Meta integration with credentials
            audience_id: Meta audience ID
            hashed_data: List of hashed user data rows

        Returns:
            Number of users received by Meta

        Raises:
            Exception: If API call fails
        """
        if not hashed_data:
            return 0

        url = f"{self.GRAPH_API_BASE}/{audience_id}/users"

        payload = {
            "payload": {
                "schema": ["EMAIL", "PHONE", "FN", "LN"],
                "is_raw": False,  # Data is already hashed
                "data": hashed_data,
            },
            "access_token": integration.access_token,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                error = response.json().get("error", {})
                raise Exception(f"Meta API error: {error.get('message', response.text)}")

            data = response.json()
            return data.get("num_received", len(hashed_data))

    async def _delete_meta_audience(
        self,
        integration: MetaIntegration,
        audience_id: str,
    ) -> bool:
        """
        Delete Custom Audience in Meta.

        Args:
            integration: Meta integration with credentials
            audience_id: Meta audience ID

        Returns:
            True if deleted

        Raises:
            Exception: If API call fails
        """
        url = f"{self.GRAPH_API_BASE}/{audience_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                url, params={"access_token": integration.access_token}
            )

            if response.status_code != 200:
                error = response.json().get("error", {})
                raise Exception(f"Meta API error: {error.get('message', response.text)}")

            return True

    async def _get_audience_size(
        self,
        integration: MetaIntegration,
        audience_id: str,
    ) -> int:
        """
        Get current audience size from Meta.

        Args:
            integration: Meta integration with credentials
            audience_id: Meta audience ID

        Returns:
            Approximate audience size
        """
        url = f"{self.GRAPH_API_BASE}/{audience_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                params={
                    "fields": "approximate_count",
                    "access_token": integration.access_token,
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("approximate_count", 0)

            return 0

    # ============== Scheduled Sync ==============

    async def sync_daily_audiences(self) -> list[AudienceSyncLog]:
        """
        Sync all audiences with daily sync mode.

        Called by scheduled task.

        Returns:
            List of sync logs
        """
        audiences, _ = await self.list_audiences(is_active=True)
        daily_audiences = [a for a in audiences if a.sync_mode == SyncMode.DAILY]

        logs = []
        for audience in daily_audiences:
            try:
                log = await self.sync_audience(audience.id)
                logs.append(log)
            except Exception as e:
                logger.error(f"Failed to sync audience {audience.name}: {e}")

        return logs
