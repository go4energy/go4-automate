"""Assistant intake service - polls sources, deduplicates events, creates items."""

import hashlib
import json
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantEvent,
    AssistantItem,
    AssistantSource,
    IntegrationConnection,
)
from app.integrations.types import CalendarEventRef, MailMessageRef


class AssistantIntakeService:
    """Fetches mail/calendar data, deduplicates, normalises into items."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_intake(self, tenant_id: str, user_id: int) -> dict:
        """Poll all active sources and ingest new data."""
        sources = await self._active_sources(tenant_id, user_id)
        if not sources:
            return {"sources": 0, "events_created": 0, "items_created": 0}

        total_events = 0
        total_items = 0

        for source in sources:
            conn = await self._get_connection(source.connection_id)
            if not conn or conn.status not in ("active", "connected"):
                continue

            try:
                events, items = await self._ingest_source(
                    tenant_id, user_id, source, conn
                )
                total_events += events
                total_items += items
            except Exception as e:
                logger.error(
                    "Intake error source={sid}: {err}",
                    sid=source.id,
                    err=str(e),
                )

        return {
            "sources": len(sources),
            "events_created": total_events,
            "items_created": total_items,
        }

    async def ingest_messages(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        messages: list[MailMessageRef],
    ) -> tuple[int, int]:
        """Ingest a list of mail messages. Returns (events_created, items_created)."""
        events_created = 0
        items_created = 0

        for msg in messages:
            payload_hash = self._hash_payload(msg.raw)
            is_new = await self._create_event_if_new(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=connection_id,
                event_type="mail_received",
                external_id=msg.provider_message_id,
                thread_id=msg.thread_id,
                payload_hash=payload_hash,
                payload=msg.raw,
                occurred_at=msg.received_at,
            )
            if not is_new:
                continue
            events_created += 1

            item = await self._upsert_item(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=connection_id,
                item_type="email",
                external_id=msg.provider_message_id,
                thread_id=msg.thread_id,
                title=msg.subject,
                content_snippet=msg.snippet,
                sender=msg.from_email,
                occurred_at=msg.received_at,
                payload_hash=payload_hash,
                raw_metadata=msg.raw,
            )
            if item:
                items_created += 1

        await self.db.flush()
        return events_created, items_created

    async def ingest_calendar_events(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        events: list[CalendarEventRef],
    ) -> tuple[int, int]:
        """Ingest calendar events. Returns (events_created, items_created)."""
        events_created = 0
        items_created = 0

        for evt in events:
            payload_hash = self._hash_payload(evt.raw)
            is_new = await self._create_event_if_new(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=connection_id,
                event_type="calendar_event",
                external_id=evt.provider_event_id,
                thread_id=None,
                payload_hash=payload_hash,
                payload=evt.raw,
                occurred_at=evt.starts_at,
            )
            if not is_new:
                continue
            events_created += 1

            item = await self._upsert_item(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=connection_id,
                item_type="calendar",
                external_id=evt.provider_event_id,
                thread_id=None,
                title=evt.title,
                content_snippet=evt.location,
                sender=evt.organizer_email,
                occurred_at=evt.starts_at,
                payload_hash=payload_hash,
                raw_metadata=evt.raw,
            )
            if item:
                items_created += 1

        await self.db.flush()
        return events_created, items_created

    # ── Private helpers ──────────────────────────────────────────────

    async def _active_sources(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantSource]:
        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.briefing_enabled.is_(True),
            )
            .order_by(AssistantSource.priority.desc())
        )
        return list(result.scalars().all())

    async def _get_connection(self, connection_id: int) -> IntegrationConnection | None:
        result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == connection_id,
            )
        )
        return result.scalar_one_or_none()

    async def _ingest_source(
        self,
        tenant_id: str,
        user_id: int,
        source: AssistantSource,
        conn: IntegrationConnection,
    ) -> tuple[int, int]:
        """Ingest from a single source via provider API. Returns (events, items)."""
        total_events = 0
        total_items = 0

        try:
            access_token = await self._ensure_access_token(conn)
        except Exception as e:
            conn.status = "error"
            conn.last_error = str(e)
            await self.db.flush()
            logger.error("Token error conn={cid}: {err}", cid=conn.id, err=str(e))
            return 0, 0

        # Determine mailbox principal for shared mailboxes
        mailbox = None
        meta = conn.metadata_json or {}
        if meta.get("scope") == "shared_mailbox" and conn.mailbox_address:
            mailbox = conn.mailbox_address

        # Fetch mail
        if source.briefing_enabled and conn.integration_type in ("email", "mail"):
            try:
                messages = await self._fetch_messages(
                    conn.provider, access_token, mailbox=mailbox
                )
                ev, it = await self.ingest_messages(
                    tenant_id, user_id, conn.id, messages
                )
                total_events += ev
                total_items += it
                logger.info(
                    "Mail intake conn={cid}: {ev} events, {it} items",
                    cid=conn.id,
                    ev=ev,
                    it=it,
                )
            except Exception as e:
                logger.error("Mail fetch conn={cid}: {err}", cid=conn.id, err=str(e))

        # Fetch calendar
        if source.briefing_enabled and conn.integration_type in (
            "calendar",
            "email",
            "mail",
        ):
            try:
                cal_events = await self._fetch_calendar(
                    conn.provider, access_token, mailbox=mailbox
                )
                ev, it = await self.ingest_calendar_events(
                    tenant_id, user_id, conn.id, cal_events
                )
                total_events += ev
                total_items += it
                logger.info(
                    "Calendar intake conn={cid}: {ev} events, {it} items",
                    cid=conn.id,
                    ev=ev,
                    it=it,
                )
            except Exception as e:
                logger.error(
                    "Calendar fetch conn={cid}: {err}", cid=conn.id, err=str(e)
                )

        # Update connection status
        conn.last_synced_at = datetime.now(UTC)
        conn.last_error = None
        conn.status = "connected"
        await self.db.flush()

        return total_events, total_items

    async def _ensure_access_token(self, conn: IntegrationConnection) -> str:
        """Decrypt token, refresh if expired, return valid access_token."""
        from app.briefing.oauth import decrypt_token, encrypt_token

        if not conn.encrypted_token:
            msg = "Kein gespeichertes Token"
            raise ValueError(msg)

        token_data = decrypt_token(conn.encrypted_token)
        access_token = token_data.get("access_token", "")
        expires_at = token_data.get("expires_at", 0)

        # Check expiration (5 min buffer)
        if datetime.now(UTC).timestamp() < expires_at - 300:
            return access_token

        # Refresh needed
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            msg = "Token abgelaufen, kein Refresh-Token vorhanden"
            raise ValueError(msg)

        refreshed = await self._refresh_token(conn.provider, refresh_token)
        token_data["access_token"] = refreshed["access_token"]
        if "refresh_token" in refreshed:
            token_data["refresh_token"] = refreshed["refresh_token"]
        token_data["expires_at"] = datetime.now(UTC).timestamp() + refreshed.get(
            "expires_in", 3600
        )

        conn.encrypted_token = encrypt_token(token_data)
        await self.db.flush()
        logger.debug("Token refreshed for conn={cid}", cid=conn.id)
        return token_data["access_token"]

    async def _refresh_token(self, provider: str, refresh_token: str) -> dict:
        """Refresh an OAuth token via the appropriate provider."""
        if provider == "microsoft_graph":
            from app.briefing.oauth import refresh_microsoft_token

            return await refresh_microsoft_token(refresh_token)
        if provider == "google_workspace":
            from app.briefing.oauth import refresh_google_token

            return await refresh_google_token(refresh_token)
        msg = f"Unbekannter Provider: {provider}"
        raise ValueError(msg)

    async def _fetch_messages(
        self,
        provider: str,
        access_token: str,
        limit: int = 30,
        mailbox: str | None = None,
    ) -> list[MailMessageRef]:
        """Fetch messages from the provider."""
        if provider == "microsoft_graph":
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient
            from app.integrations.microsoft_graph.mail_read import (
                MicrosoftGraphMailReadProvider,
            )

            client = MicrosoftGraphClient(access_token)
            mail_provider = MicrosoftGraphMailReadProvider(client)
            return await mail_provider.list_messages(limit=limit, mailbox=mailbox)

        logger.warning("Mail fetch not implemented for provider={p}", p=provider)
        return []

    async def _fetch_calendar(
        self,
        provider: str,
        access_token: str,
        limit: int = 20,
        mailbox: str | None = None,
    ) -> list[CalendarEventRef]:
        """Fetch calendar events from the provider."""
        if provider == "microsoft_graph":
            from app.integrations.microsoft_graph.calendar import (
                MicrosoftGraphCalendarProvider,
            )
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient

            client = MicrosoftGraphClient(access_token)
            cal_provider = MicrosoftGraphCalendarProvider(client)
            return await cal_provider.list_events(limit=limit, mailbox=mailbox)

        logger.warning("Calendar fetch not implemented for provider={p}", p=provider)
        return []

    async def _create_event_if_new(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        event_type: str,
        external_id: str,
        thread_id: str | None,
        payload_hash: str,
        payload: dict | None,
        occurred_at: datetime | None,
    ) -> bool:
        """Create event if not already seen (dedup by hash). Returns True if new."""
        existing = await self.db.execute(
            select(AssistantEvent.id).where(
                AssistantEvent.tenant_id == tenant_id,
                AssistantEvent.connection_id == connection_id,
                AssistantEvent.external_id == external_id,
                AssistantEvent.raw_payload_hash == payload_hash,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return False

        event = AssistantEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=connection_id,
            event_type=event_type,
            external_id=external_id,
            thread_id=thread_id,
            raw_payload_hash=payload_hash,
            payload_json=payload,
            occurred_at=occurred_at,
        )
        self.db.add(event)
        return True

    async def _upsert_item(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        item_type: str,
        external_id: str,
        thread_id: str | None,
        title: str | None,
        content_snippet: str | None,
        sender: str | None,
        occurred_at: datetime | None,
        payload_hash: str,
        raw_metadata: dict | None,
    ) -> AssistantItem | None:
        """Create or update an item. Returns item if newly created."""
        existing = await self.db.execute(
            select(AssistantItem).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.connection_id == connection_id,
                AssistantItem.external_id == external_id,
            )
        )
        item = existing.scalar_one_or_none()
        if item:
            item.title = title
            item.content_snippet = content_snippet
            item.raw_payload_hash = payload_hash
            item.raw_metadata_json = raw_metadata
            return None

        item = AssistantItem(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=connection_id,
            item_type=item_type,
            external_id=external_id,
            thread_id=thread_id,
            title=title,
            content_snippet=content_snippet,
            sender=sender,
            occurred_at=occurred_at,
            raw_payload_hash=payload_hash,
            raw_metadata_json=raw_metadata,
        )
        self.db.add(item)
        return item

    @staticmethod
    def _hash_payload(payload: dict | None) -> str:
        """SHA-256 hash of JSON-serialised payload for dedup."""
        raw = json.dumps(payload or {}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()
