"""Assistant rule engine - applies user rules before LLM classification."""

import re

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantAction, AssistantItem, AssistantRule


class AssistantRuleEngine:
    """Evaluates items against user-defined rules, creates actions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def apply_rules(
        self,
        tenant_id: str,
        user_id: int,
        items: list[AssistantItem],
    ) -> list[AssistantAction]:
        """Apply all enabled rules to a batch of items."""
        rules = await self._load_rules(tenant_id, user_id)
        if not rules:
            return []

        actions = []
        for item in items:
            for rule in rules:
                if self._matches(rule, item):
                    action = self._create_action(tenant_id, user_id, item, rule)
                    self.db.add(action)
                    actions.append(action)
                    logger.debug(
                        "Rule '{name}' matched item {iid}",
                        name=rule.name,
                        iid=item.id,
                    )
                    break  # first matching rule wins

        await self.db.flush()
        return actions

    async def _load_rules(self, tenant_id: str, user_id: int) -> list[AssistantRule]:
        result = await self.db.execute(
            select(AssistantRule)
            .where(
                AssistantRule.tenant_id == tenant_id,
                AssistantRule.user_id == user_id,
                AssistantRule.enabled.is_(True),
            )
            .order_by(AssistantRule.priority.desc(), AssistantRule.id)
        )
        return list(result.scalars().all())

    def _matches(self, rule: AssistantRule, item: AssistantItem) -> bool:
        """Check if rule criteria match the item."""
        criteria = rule.match_criteria_json
        if not criteria:
            return False

        title = (item.title or "").lower()
        sender = (item.sender or "").lower()
        snippet = (item.content_snippet or "").lower()

        # sender_domain match
        if "sender_domain" in criteria:
            domain = criteria["sender_domain"].lower()
            if domain not in sender:
                return False

        # sender_contains match
        if "sender_contains" in criteria:
            pattern = criteria["sender_contains"].lower()
            if pattern not in sender:
                return False

        # subject_contains match
        if "subject_contains" in criteria:
            pattern = criteria["subject_contains"].lower()
            if pattern not in title:
                return False

        # subject_regex match
        if "subject_regex" in criteria:
            try:
                if not re.search(
                    criteria["subject_regex"], item.title or "", re.IGNORECASE
                ):
                    return False
            except re.error:
                return False

        # item_type match
        if "item_type" in criteria and item.item_type != criteria["item_type"]:
            return False

        # keywords match (any keyword in title or snippet)
        if "keywords" in criteria:
            keywords = [k.lower() for k in criteria["keywords"]]
            if not any(kw in title or kw in snippet for kw in keywords):
                return False

        return True

    @staticmethod
    def _create_action(
        tenant_id: str,
        user_id: int,
        item: AssistantItem,
        rule: AssistantRule,
    ) -> AssistantAction:
        """Create an action from a matched rule."""
        requires_confirmation = rule.risk_level in ("medium", "high")

        return AssistantAction(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=item.id,
            action_type=rule.action_type,
            status="suggested" if requires_confirmation else "queued",
            risk_level=rule.risk_level,
            requires_confirmation=requires_confirmation,
            metadata_json={
                "rule_id": rule.id,
                "rule_name": rule.name,
                **(rule.action_payload_json or {}),
            },
        )
