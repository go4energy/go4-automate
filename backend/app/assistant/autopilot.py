"""Autopilot service — automatic mailbox cleanup based on learned rules."""

import re

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantAction,
    AssistantItem,
    AssistantProfile,
    AssistantRule,
    AssistantSource,
    AssistantUndoLog,
    IntegrationConnection,
)
from app.integrations.microsoft_graph.client import MicrosoftGraphClient
from app.integrations.microsoft_graph.mail_actions import (
    MicrosoftGraphMailActionProvider,
)
from app.integrations.microsoft_graph.mail_read import (
    MicrosoftGraphMailReadProvider,
)
from app.integrations.types import MailMessageRef

# Risk ordering for trust-gate comparison
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


class AutopilotService:
    """Runs automatic mailbox cleanup cycles based on rules and trust settings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_autopilot_cycle(self, tenant_id: str, user_id: int) -> dict:
        """Run one autopilot cycle for a single user.

        Returns stats dict with counts of actions taken.
        """
        profile = await self._load_profile(tenant_id, user_id)
        if not profile or not profile.autopilot_enabled:
            return {"skipped": True, "reason": "autopilot_disabled"}

        sources = await self._load_autopilot_sources(tenant_id, user_id)
        if not sources:
            return {"skipped": True, "reason": "no_autopilot_sources"}

        rules = await self._load_enabled_rules(tenant_id, user_id)
        if not rules:
            return {"skipped": True, "reason": "no_rules"}

        stats = {
            "sources_processed": 0,
            "emails_scanned": 0,
            "auto_executed": 0,
            "queued_for_review": 0,
            "skipped_high_risk": 0,
            "errors": 0,
        }

        for source in sources:
            try:
                source_stats = await self._process_source(
                    tenant_id, user_id, profile, source, rules
                )
                stats["sources_processed"] += 1
                stats["emails_scanned"] += source_stats["emails_scanned"]
                stats["auto_executed"] += source_stats["auto_executed"]
                stats["queued_for_review"] += source_stats["queued_for_review"]
                stats["skipped_high_risk"] += source_stats["skipped_high_risk"]
            except Exception:
                stats["errors"] += 1
                logger.exception("Autopilot source error: source={sid}", sid=source.id)

        logger.info(
            "Autopilot cycle: tenant={t} user={u} scanned={s} exec={e} queued={q}",
            t=tenant_id,
            u=user_id,
            s=stats["emails_scanned"],
            e=stats["auto_executed"],
            q=stats["queued_for_review"],
        )
        return stats

    async def _process_source(
        self,
        tenant_id: str,
        user_id: int,
        profile: AssistantProfile,
        source: AssistantSource,
        rules: list[AssistantRule],
    ) -> dict:
        """Process a single autopilot-enabled source."""
        from app.assistant.intake import AssistantIntakeService

        conn = await self._get_connection(source.connection_id)
        if not conn or conn.status not in ("active", "connected"):
            return {
                "emails_scanned": 0,
                "auto_executed": 0,
                "queued_for_review": 0,
                "skipped_high_risk": 0,
            }

        intake = AssistantIntakeService(self.db)
        access_token = await intake._ensure_access_token(conn)

        mailbox = conn.mailbox_address or conn.connected_email
        client = MicrosoftGraphClient(access_token)
        reader = MicrosoftGraphMailReadProvider(client)

        messages = await reader.list_messages(
            mailbox=mailbox, unread_only=True, limit=10
        )

        stats = {
            "emails_scanned": len(messages),
            "auto_executed": 0,
            "queued_for_review": 0,
            "skipped_high_risk": 0,
        }
        actions_provider = MicrosoftGraphMailActionProvider(client)
        folder_cache: dict[str, str] = {}

        for message in messages:
            matched_rule = self._find_matching_rule(rules, message, mailbox, profile)
            if not matched_rule:
                continue

            decision = self._trust_gate(matched_rule, profile)

            if decision == "execute":
                success = await self._execute_action(
                    tenant_id,
                    user_id,
                    conn.id,
                    matched_rule,
                    message,
                    mailbox,
                    actions_provider,
                    folder_cache,
                    access_token,
                )
                if success:
                    stats["auto_executed"] += 1
            elif decision == "queue":
                await self._queue_for_review(
                    tenant_id, user_id, conn.id, matched_rule, message
                )
                stats["queued_for_review"] += 1
            else:
                stats["skipped_high_risk"] += 1

        return stats

    def _find_matching_rule(
        self,
        rules: list[AssistantRule],
        message: MailMessageRef,
        mailbox: str | None,
        profile: AssistantProfile,
    ) -> AssistantRule | None:
        """Find the first matching rule that passes confidence threshold."""
        for rule in rules:
            if not self._rule_matches_message(rule, message, mailbox):
                continue
            if rule.confidence and rule.confidence < profile.autopilot_min_confidence:
                continue
            return rule
        return None

    def _trust_gate(self, rule: AssistantRule, profile: AssistantProfile) -> str:
        """Determine action based on rule risk vs profile max risk.

        Returns: "execute", "queue", or "skip"
        """
        rule_risk = _RISK_ORDER.get(rule.risk_level, 2)
        max_risk = _RISK_ORDER.get(profile.autopilot_max_rule_risk, 1)

        # Delete actions are ALWAYS queued, never auto-executed
        if rule.action_type == "delete":
            return "queue"

        # Low risk: always execute
        if rule_risk == 0:
            return "execute"

        # Medium risk: execute only if profile allows medium+
        if rule_risk == 1:
            return "execute" if max_risk >= 1 else "skip"

        # High risk: always queue
        return "queue"

    async def _execute_action(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        rule: AssistantRule,
        message: MailMessageRef,
        mailbox: str | None,
        actions: MicrosoftGraphMailActionProvider,
        folder_cache: dict[str, str],
        access_token: str,
    ) -> bool:
        """Execute a rule action (move) and log to undo."""
        try:
            action_type = rule.action_type
            folder_name = (rule.action_payload_json or {}).get("target", "Archive")

            if action_type in ("move", "archive"):
                folder_id = folder_cache.get(folder_name.lower())
                if not folder_id:
                    folder_id = await self._resolve_folder_id(
                        access_token, mailbox, folder_name
                    )
                    if folder_id:
                        folder_cache[folder_name.lower()] = folder_id

                if not folder_id:
                    logger.warning(
                        "Autopilot: folder '{f}' not found for mailbox={m}",
                        f=folder_name,
                        m=mailbox,
                    )
                    return False

                await actions.move_message(
                    message.provider_message_id,
                    folder_id,
                    mailbox=mailbox,
                )
                # Mark as read after move (autopilot always archives)
                try:
                    await actions.update_message(
                        message.provider_message_id,
                        {"isRead": True},
                        mailbox=mailbox,
                    )
                except Exception:
                    logger.warning("Autopilot: could not mark as read")

                await self._write_undo_log(
                    tenant_id,
                    user_id,
                    connection_id,
                    action_type="move",
                    message=message,
                    before_folder_id=(message.raw or {}).get("parentFolderId"),
                    after_folder_id=folder_id,
                    after_folder_name=folder_name,
                    rule_name=rule.name,
                )
                return True

            return False

        except Exception:
            logger.exception(
                "Autopilot execute failed: msg={mid} rule={rn}",
                mid=message.provider_message_id,
                rn=rule.name,
            )
            return False

    async def _queue_for_review(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        rule: AssistantRule,
        message: MailMessageRef,
    ) -> None:
        """Create a suggested AssistantAction for manual review."""
        # First ensure the item exists
        item = await self._get_or_create_item(
            tenant_id, user_id, connection_id, message
        )

        action = AssistantAction(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=item.id,
            action_type=rule.action_type,
            status="suggested",
            risk_level=rule.risk_level,
            requires_confirmation=True,
            metadata_json={
                "autopilot": True,
                "rule_id": rule.id,
                "rule_name": rule.name,
                "target": (rule.action_payload_json or {}).get("target"),
            },
        )
        self.db.add(action)
        await self.db.flush()

    async def _get_or_create_item(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        message: MailMessageRef,
    ) -> AssistantItem:
        """Get existing item or create a minimal one for the message."""
        result = await self.db.execute(
            select(AssistantItem).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.connection_id == connection_id,
                AssistantItem.external_id == message.provider_message_id,
            )
        )
        item = result.scalar_one_or_none()
        if item:
            return item

        item = AssistantItem(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=connection_id,
            item_type="email",
            external_id=message.provider_message_id,
            thread_id=message.thread_id,
            title=message.subject,
            sender=message.from_email,
            content_snippet=message.snippet,
            occurred_at=message.received_at.replace(tzinfo=None)
            if message.received_at
            else None,
            status="new",
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def _write_undo_log(
        self,
        tenant_id: str,
        user_id: int,
        connection_id: int,
        *,
        action_type: str,
        message: MailMessageRef,
        before_folder_id: str | None,
        after_folder_id: str,
        after_folder_name: str,
        rule_name: str,
    ) -> None:
        """Write an undo log entry for an autopilot action."""
        log = AssistantUndoLog(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=connection_id,
            action_type=action_type,
            status="executed",
            can_undo=True,
            target_ref_json={
                "message_id": message.provider_message_id,
                "subject": message.subject,
                "sender": message.from_email,
            },
            before_state_json={"folder_id": before_folder_id},
            after_state_json={
                "folder_id": after_folder_id,
                "folder_name": after_folder_name,
            },
            metadata_json={
                "autopilot": True,
                "rule_name": rule_name,
            },
        )
        self.db.add(log)
        await self.db.flush()

    # ── Helpers ────────────────────────────────────────────────────

    def _rule_matches_message(
        self, rule: AssistantRule, message: MailMessageRef, mailbox: str | None
    ) -> bool:
        """Check if a rule matches a message (replicates tool_executor logic)."""
        criteria = rule.match_criteria_json or {}
        if not criteria:
            return False
        title = (message.subject or "").lower()
        sender = (message.from_email or "").lower()
        snippet = (message.snippet or "").lower()

        if (
            "sender_domain" in criteria
            and criteria["sender_domain"].lower() not in sender
        ):
            return False
        if (
            "sender_contains" in criteria
            and criteria["sender_contains"].lower() not in sender
        ):
            return False
        if (
            "subject_contains" in criteria
            and criteria["subject_contains"].lower() not in title
        ):
            return False
        if "subject_regex" in criteria:
            try:
                if not re.search(
                    criteria["subject_regex"], message.subject or "", re.IGNORECASE
                ):
                    return False
            except re.error:
                return False
        if "keywords" in criteria:
            keywords = [k.lower() for k in criteria["keywords"]]
            if not any(kw in title or kw in snippet for kw in keywords):
                return False
        return not (
            "mailbox" in criteria
            and (mailbox or "").lower() != criteria["mailbox"].lower()
        )

    async def _load_profile(
        self, tenant_id: str, user_id: int
    ) -> AssistantProfile | None:
        result = await self.db.execute(
            select(AssistantProfile).where(
                AssistantProfile.tenant_id == tenant_id,
                AssistantProfile.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_autopilot_sources(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantSource]:
        result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.autopilot_enabled.is_(True),
            )
        )
        return list(result.scalars().all())

    async def _load_enabled_rules(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantRule]:
        result = await self.db.execute(
            select(AssistantRule)
            .where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.enabled.is_(True),
            )
            .order_by(AssistantRule.priority.desc(), AssistantRule.id.asc())
        )
        return list(result.scalars().all())

    async def _get_connection(self, connection_id: int) -> IntegrationConnection | None:
        return await self.db.get(IntegrationConnection, connection_id)

    async def _resolve_folder_id(
        self, access_token: str, mailbox: str | None, folder_name: str
    ) -> str | None:
        """Resolve folder display name to Graph folder ID."""
        client = MicrosoftGraphClient(access_token)
        principal = f"users/{mailbox}" if mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={"$select": "id,displayName", "$top": "100"},
        )
        for folder in data.get("value", []):
            if folder.get("displayName", "").lower() == folder_name.lower():
                return folder.get("id")
        return None
