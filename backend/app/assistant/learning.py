"""Assistant learning service - derives rules from user feedback."""

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantFeedback, AssistantItem, AssistantRule


class AssistantLearningService:
    """Analyses feedback patterns and suggests rules."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def suggest_rules(self, tenant_id: str, user_id: int) -> list[dict]:
        """Analyse feedback and suggest new rules."""
        suggestions = []

        # Find repeated feedback patterns by sender
        sender_patterns = await self._find_sender_patterns(tenant_id, user_id)
        for pattern in sender_patterns:
            suggestions.append(pattern)

        logger.info(
            "Generated {n} rule suggestions for user {uid}",
            n=len(suggestions),
            uid=user_id,
        )
        return suggestions

    async def apply_suggestion(
        self,
        tenant_id: str,
        user_id: int,
        suggestion: dict,
    ) -> AssistantRule:
        """Convert a suggestion into a saved rule."""
        rule = AssistantRule(
            tenant_id=tenant_id,
            user_id=user_id,
            name=suggestion.get("name", "Gelernte Regel"),
            scope="user",
            priority=suggestion.get("priority", 10),
            match_criteria_json=suggestion.get("match_criteria"),
            action_type=suggestion.get("action_type", "label"),
            action_payload_json=suggestion.get("action_payload"),
            risk_level=suggestion.get("risk_level", "low"),
            origin="learned",
            confidence=suggestion.get("confidence", 0.7),
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        logger.info("Applied rule suggestion: {name}", name=rule.name)
        return rule

    async def _find_sender_patterns(self, tenant_id: str, user_id: int) -> list[dict]:
        """Find senders with repeated feedback of the same type."""
        # Get feedback with associated items
        result = await self.db.execute(
            select(
                AssistantItem.sender,
                AssistantFeedback.feedback_type,
                func.count(AssistantFeedback.id).label("count"),
            )
            .join(AssistantItem, AssistantFeedback.item_id == AssistantItem.id)
            .where(
                AssistantFeedback.tenant_id == tenant_id,
                AssistantFeedback.user_id == user_id,
                AssistantItem.sender.isnot(None),
            )
            .group_by(AssistantItem.sender, AssistantFeedback.feedback_type)
            .having(func.count(AssistantFeedback.id) >= 3)
        )
        rows = result.all()

        suggestions = []
        action_map = {
            "ignore": "mute",
            "move": "move",
            "delete": "archive",
            "keep": "prioritize",
        }

        for sender, feedback_type, count in rows:
            # Check if rule already exists
            existing = await self.db.execute(
                select(AssistantRule.id).where(
                    AssistantRule.tenant_id == tenant_id,
                    AssistantRule.user_id == user_id,
                    AssistantRule.match_criteria_json["sender_contains"].as_string()
                    == sender,
                )
            )
            if existing.scalar_one_or_none():
                continue

            action_type = action_map.get(feedback_type, "label")
            suggestions.append(
                {
                    "name": f"Mails von {sender}: {feedback_type}",
                    "match_criteria": {"sender_contains": sender},
                    "action_type": action_type,
                    "risk_level": "low",
                    "confidence": min(0.5 + count * 0.1, 0.95),
                    "priority": 10,
                    "reason": f"{count}x '{feedback_type}' fuer Absender {sender}",
                }
            )

        return suggestions
