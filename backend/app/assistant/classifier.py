"""Assistant classifier - relevance scoring and item classification."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantDecision, AssistantItem


class AssistantClassifier:
    """Classifies items by importance, reply-need, and briefing suitability."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def classify_items(
        self,
        tenant_id: str,
        user_id: int,
        items: list[AssistantItem],
    ) -> list[AssistantDecision]:
        """Run rule-based classification on a batch of items."""
        decisions = []
        for item in items:
            decision = await self._classify_single(tenant_id, user_id, item)
            decisions.append(decision)
        await self.db.flush()
        return decisions

    async def _classify_single(
        self,
        tenant_id: str,
        user_id: int,
        item: AssistantItem,
    ) -> AssistantDecision:
        """Classify a single item using rule-based heuristics."""
        importance = self._estimate_importance(item)
        needs_reply = self._estimate_needs_reply(item)

        decision = AssistantDecision(
            tenant_id=tenant_id,
            user_id=user_id,
            item_id=item.id,
            decision_type="importance",
            decision_value=importance,
            confidence=0.7,
            reason=self._build_reason(item, importance),
            source="rule",
        )
        self.db.add(decision)

        if needs_reply:
            reply_decision = AssistantDecision(
                tenant_id=tenant_id,
                user_id=user_id,
                item_id=item.id,
                decision_type="needs_reply",
                decision_value="yes",
                confidence=0.6,
                reason="Direktnachricht erkannt",
                source="rule",
            )
            self.db.add(reply_decision)

        item.status = "classified"
        return decision

    def _estimate_importance(self, item: AssistantItem) -> str:
        """Rule-based importance estimation."""
        title = (item.title or "").lower()
        sender = (item.sender or "").lower()

        # High importance signals
        high_signals = ["dringend", "urgent", "asap", "wichtig", "deadline"]
        if any(s in title for s in high_signals):
            return "high"

        # Calendar events are generally important
        if item.item_type == "calendar":
            return "high"

        # Newsletter / automated mail signals
        low_signals = [
            "newsletter",
            "unsubscribe",
            "noreply",
            "no-reply",
            "notification",
            "digest",
            "weekly",
            "monthly",
        ]
        if any(s in title or s in sender for s in low_signals):
            return "low"

        return "medium"

    def _estimate_needs_reply(self, item: AssistantItem) -> bool:
        """Estimate whether the item likely needs a reply."""
        if item.item_type == "calendar":
            return False
        sender = (item.sender or "").lower()
        # Automated senders typically don't need replies
        no_reply_patterns = ["noreply", "no-reply", "notification", "mailer-daemon"]
        return not any(p in sender for p in no_reply_patterns)

    @staticmethod
    def _build_reason(item: AssistantItem, importance: str) -> str:
        """Build a human-readable reason string."""
        if importance == "high":
            if item.item_type == "calendar":
                return "Kalendereintrag"
            return "Dringendes Signal im Betreff"
        if importance == "low":
            return "Newsletter oder automatische Benachrichtigung"
        return "Standardnachricht"
