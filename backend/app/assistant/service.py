"""Assistant module business logic."""

from datetime import UTC

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantAction,
    AssistantDecision,
    AssistantFeedback,
    AssistantItem,
    AssistantProfile,
    AssistantRule,
    AssistantSource,
    IntegrationConnection,
)
from app.exceptions import DuplicateError, NotFoundError, ValidationError


class AssistantService:
    """Orchestrates assistant profile, sources, and sub-services."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Profile ──────────────────────────────────────────────────────

    async def get_or_create_profile(
        self, tenant_id: str, user_id: int
    ) -> AssistantProfile:
        """Return existing profile or create a default one."""
        result = await self.db.execute(
            select(AssistantProfile).where(
                AssistantProfile.tenant_id == tenant_id,
                AssistantProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if profile:
            return profile

        profile = AssistantProfile(tenant_id=tenant_id, user_id=user_id)
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        logger.info("Created assistant profile for user {uid}", uid=user_id)
        return profile

    async def update_profile(
        self, tenant_id: str, user_id: int, updates: dict
    ) -> AssistantProfile:
        """Partial-update the user's assistant profile."""
        profile = await self.get_or_create_profile(tenant_id, user_id)
        for key, value in updates.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    # ── Sources ──────────────────────────────────────────────────────

    async def list_sources(self, tenant_id: str, user_id: int) -> list[dict]:
        """List all assistant sources with connection details."""
        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
            )
            .order_by(AssistantSource.priority.desc(), AssistantSource.id)
        )
        sources = list(result.scalars().all())

        enriched = []
        for source in sources:
            conn_result = await self.db.execute(
                select(IntegrationConnection).where(
                    IntegrationConnection.id == source.connection_id,
                )
            )
            conn = conn_result.scalar_one_or_none()
            source_dict = {
                "id": source.id,
                "tenant_id": source.tenant_id,
                "user_id": source.user_id,
                "connection_id": source.connection_id,
                "briefing_enabled": source.briefing_enabled,
                "voice_enabled": source.voice_enabled,
                "reply_enabled": source.reply_enabled,
                "autopilot_enabled": source.autopilot_enabled,
                "priority": source.priority,
                "settings_json": source.settings_json,
                "created_at": source.created_at,
                "updated_at": source.updated_at,
                "connection": None,
            }
            if conn:
                source_dict["connection"] = {
                    "id": conn.id,
                    "provider": conn.provider,
                    "integration_type": conn.integration_type,
                    "connected_email": conn.connected_email,
                    "mailbox_address": conn.mailbox_address,
                    "account_label": conn.account_label,
                    "status": conn.status,
                    "last_synced_at": conn.last_synced_at,
                    "last_error": conn.last_error,
                }
            enriched.append(source_dict)
        return enriched

    async def add_source(
        self, tenant_id: str, user_id: int, data: dict
    ) -> AssistantSource:
        """Add an integration connection as assistant source."""
        connection_id = data["connection_id"]

        # Verify connection exists and belongs to tenant/user
        conn = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == connection_id,
                IntegrationConnection.tenant_id == tenant_id,
            )
        )
        if not conn.scalar_one_or_none():
            raise NotFoundError("IntegrationConnection", connection_id)

        # Check for duplicate
        existing = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == connection_id,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("AssistantSource", "connection_id")

        source = AssistantSource(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def update_source(
        self, tenant_id: str, user_id: int, source_id: int, updates: dict
    ) -> AssistantSource:
        """Partial-update an assistant source."""
        source = await self._get_source(tenant_id, user_id, source_id)
        for key, value in updates.items():
            if value is not None and hasattr(source, key):
                setattr(source, key, value)
        await self.db.flush()
        await self.db.refresh(source)
        return source

    async def delete_source(self, tenant_id: str, user_id: int, source_id: int) -> None:
        """Remove an assistant source."""
        source = await self._get_source(tenant_id, user_id, source_id)
        await self.db.delete(source)
        await self.db.flush()

    async def _get_source(
        self, tenant_id: str, user_id: int, source_id: int
    ) -> AssistantSource:
        result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.id == source_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("AssistantSource", source_id)
        return source

    # ── Items ────────────────────────────────────────────────────────

    async def list_items(
        self,
        tenant_id: str,
        user_id: int,
        status: str | None = None,
        item_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AssistantItem]:
        """List assistant items with optional filters."""
        query = (
            select(AssistantItem)
            .where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
            )
            .order_by(AssistantItem.occurred_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        if status:
            query = query.where(AssistantItem.status == status)
        if item_type:
            query = query.where(AssistantItem.item_type == item_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_item(
        self, tenant_id: str, user_id: int, item_id: int
    ) -> AssistantItem:
        """Get a single item."""
        result = await self.db.execute(
            select(AssistantItem).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
                AssistantItem.id == item_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("AssistantItem", item_id)
        return item

    # ── Rules ────────────────────────────────────────────────────────

    async def list_rules(self, tenant_id: str, user_id: int) -> list[AssistantRule]:
        """List all rules for a user."""
        result = await self.db.execute(
            select(AssistantRule)
            .where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
            )
            .order_by(AssistantRule.priority.desc(), AssistantRule.id)
        )
        return list(result.scalars().all())

    async def create_rule(
        self, tenant_id: str, user_id: int, data: dict
    ) -> AssistantRule:
        """Create a new triage rule."""
        allowed_risk = {"low", "medium", "high"}
        if data.get("risk_level", "low") not in allowed_risk:
            raise ValidationError(f"risk_level muss eines von {allowed_risk} sein")

        rule = AssistantRule(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        logger.info("Created rule '{name}' for user {uid}", name=rule.name, uid=user_id)
        return rule

    async def update_rule(
        self, tenant_id: str, user_id: int, rule_id: int, updates: dict
    ) -> AssistantRule:
        """Partial-update a rule."""
        result = await self.db.execute(
            select(AssistantRule).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.id == rule_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("AssistantRule", rule_id)

        for key, value in updates.items():
            if value is not None and hasattr(rule, key):
                setattr(rule, key, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, tenant_id: str, user_id: int, rule_id: int) -> None:
        """Delete a rule."""
        result = await self.db.execute(
            select(AssistantRule).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.id == rule_id,
            )
        )
        rule = result.scalar_one_or_none()
        if not rule:
            raise NotFoundError("AssistantRule", rule_id)
        await self.db.delete(rule)
        await self.db.flush()

    # ── Actions ──────────────────────────────────────────────────────

    async def list_pending_actions(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantAction]:
        """List actions awaiting approval."""
        result = await self.db.execute(
            select(AssistantAction)
            .where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.status.in_(["suggested", "queued"]),
            )
            .order_by(AssistantAction.created_at.desc())
        )
        return list(result.scalars().all())

    async def approve_action(
        self, tenant_id: str, user_id: int, action_id: int
    ) -> AssistantAction:
        """Approve a pending action."""
        result = await self.db.execute(
            select(AssistantAction).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.id == action_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("AssistantAction", action_id)
        if action.status not in ("suggested", "queued"):
            raise ValidationError(
                f"Aktion hat Status '{action.status}', kann nicht freigegeben werden"
            )
        action.status = "queued"
        await self.db.flush()
        await self.db.refresh(action)
        return action

    async def reject_action(
        self, tenant_id: str, user_id: int, action_id: int
    ) -> AssistantAction:
        """Reject a pending action."""
        result = await self.db.execute(
            select(AssistantAction).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.id == action_id,
            )
        )
        action = result.scalar_one_or_none()
        if not action:
            raise NotFoundError("AssistantAction", action_id)
        action.status = "rejected"
        await self.db.flush()
        await self.db.refresh(action)
        return action

    # ── Feedback ─────────────────────────────────────────────────────

    async def add_feedback(
        self, tenant_id: str, user_id: int, item_id: int, data: dict
    ) -> AssistantFeedback:
        """Record user feedback on an item."""
        # Verify item exists
        await self.get_item(tenant_id, user_id, item_id)

        feedback = AssistantFeedback(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=item_id,
            **data,
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    # ── Decisions (read) ─────────────────────────────────────────────

    async def list_decisions_for_item(
        self, tenant_id: str, user_id: int, item_id: int
    ) -> list[AssistantDecision]:
        """List all decisions for a specific item."""
        result = await self.db.execute(
            select(AssistantDecision)
            .where(
                AssistantDecision.tenant_id == tenant_id,
                AssistantDecision.user_id == user_id,
                AssistantDecision.item_id == item_id,
            )
            .order_by(AssistantDecision.created_at.desc())
        )
        return list(result.scalars().all())

    # ── Stats ────────────────────────────────────────────────────────

    async def get_dashboard_stats(self, tenant_id: str, user_id: int) -> dict:
        """Return quick dashboard stats."""
        from sqlalchemy import func

        items_q = await self.db.execute(
            select(func.count(AssistantItem.id)).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.user_id == user_id,
            )
        )
        rules_q = await self.db.execute(
            select(func.count(AssistantRule.id)).where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.enabled.is_(True),
            )
        )
        pending_q = await self.db.execute(
            select(func.count(AssistantAction.id)).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.status.in_(["suggested", "queued"]),
            )
        )
        sources_q = await self.db.execute(
            select(func.count(AssistantSource.id)).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
            )
        )

        return {
            "total_items": items_q.scalar() or 0,
            "active_rules": rules_q.scalar() or 0,
            "pending_actions": pending_q.scalar() or 0,
            "connected_sources": sources_q.scalar() or 0,
        }

    # ── Connection + Source ─────────────────────────────────────────

    async def create_connection_and_source(
        self,
        tenant_id: str,
        user_id: int,
        provider: str,
        connected_email: str,
        encrypted_token: str,
        mailbox_address: str | None = None,
        scope: str = "personal",
    ) -> tuple[IntegrationConnection, AssistantSource]:
        """Create an IntegrationConnection and link it as AssistantSource."""
        from app.assistant.models import IntegrationConnectionCapability

        effective_mailbox = mailbox_address or connected_email
        label = f"{effective_mailbox} (Shared)" if mailbox_address else connected_email

        # Upsert connection (match on mailbox, not just email)
        existing = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == tenant_id,
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == provider,
                IntegrationConnection.mailbox_address == effective_mailbox,
            )
        )
        conn = existing.scalar_one_or_none()
        if conn:
            conn.encrypted_token = encrypted_token
            conn.status = "connected"
            conn.last_error = None
        else:
            conn = IntegrationConnection(
                tenant_id=tenant_id,
                user_id=user_id,
                provider=provider,
                integration_type="email",
                auth_mode="delegated",
                connected_email=connected_email,
                mailbox_address=effective_mailbox,
                account_label=label,
                encrypted_token=encrypted_token,
                status="connected",
                metadata_json={"scope": scope},
            )
            self.db.add(conn)
            await self.db.flush()

            # Grant capabilities
            for cap in ("read_mail", "read_calendar"):
                self.db.add(
                    IntegrationConnectionCapability(
                        connection_id=conn.id,
                        capability=cap,
                        granted=True,
                    )
                )

        await self.db.flush()
        await self.db.refresh(conn)

        # Ensure source exists
        source_result = await self.db.execute(
            select(AssistantSource).where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.connection_id == conn.id,
            )
        )
        source = source_result.scalar_one_or_none()
        if not source:
            source = AssistantSource(
                tenant_id=tenant_id,
                user_id=user_id,
                connection_id=conn.id,
                briefing_enabled=True,
            )
            self.db.add(source)
            await self.db.flush()
            await self.db.refresh(source)

        return conn, source

    # ── Briefing ─────────────────────────────────────────────────────

    async def run_briefing(
        self,
        tenant_id: str,
        user_id: int,
        max_items: int = 30,
    ) -> dict:
        """Run a briefing: intake → classify → rules → generate text."""
        from datetime import datetime

        from app.assistant.classifier import AssistantClassifier
        from app.assistant.intake import AssistantIntakeService
        from app.assistant.rules import AssistantRuleEngine

        # 1. Intake
        intake = AssistantIntakeService(self.db)
        intake_result = await intake.run_intake(tenant_id, user_id)
        logger.info("Intake: {r}", r=intake_result)

        # 2. Get recent unclassified items
        items = await self.list_items(tenant_id, user_id, status="new", limit=max_items)

        # 3. Classify
        classifier = AssistantClassifier(self.db)
        decisions = await classifier.classify_items(tenant_id, user_id, items)

        # 4. Apply rules
        rule_engine = AssistantRuleEngine(self.db)
        actions = await rule_engine.apply_rules(tenant_id, user_id, items)

        # 5. Build briefing text
        briefing_text = self._build_briefing_text(items, decisions)

        await self.db.flush()

        return {
            "items_processed": len(items),
            "briefing_text": briefing_text,
            "audio_url": None,
            "generated_at": datetime.now(UTC).isoformat(),
            "actions_created": len(actions),
        }

    @staticmethod
    def _build_briefing_text(
        items: list[AssistantItem],
        decisions: list[AssistantDecision],
    ) -> str:
        """Build a simple text briefing from classified items."""
        if not items:
            return "Keine neuen Nachrichten oder Termine."

        # Map item_id -> importance
        importance_map: dict[int, str] = {}
        for d in decisions:
            if d.decision_type == "importance":
                importance_map[d.item_id] = d.decision_value or "medium"

        lines = []
        high_items = [i for i in items if importance_map.get(i.id) == "high"]
        medium_items = [i for i in items if importance_map.get(i.id) == "medium"]
        low_items = [i for i in items if importance_map.get(i.id) == "low"]

        if high_items:
            lines.append(f"Wichtig ({len(high_items)}):")
            for item in high_items[:10]:
                lines.append(f"  - {item.title or '(ohne Betreff)'}")
                if item.sender:
                    lines[-1] += f" (von {item.sender})"

        if medium_items:
            lines.append(f"\nInformativ ({len(medium_items)}):")
            for item in medium_items[:10]:
                lines.append(f"  - {item.title or '(ohne Betreff)'}")

        if low_items:
            lines.append(f"\nNiedrige Prioritaet ({len(low_items)}):")
            lines.append(
                f"  {len(low_items)} Nachrichten (Newsletter, Benachrichtigungen)"
            )

        return "\n".join(lines)
