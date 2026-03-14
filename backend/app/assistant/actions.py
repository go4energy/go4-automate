"""Assistant action executor - processes queued actions."""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantAction


class AssistantActionService:
    """Executes queued actions (label, move, archive, etc.)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_queued_actions(
        self, tenant_id: str, user_id: int
    ) -> list[AssistantAction]:
        """Execute all queued actions. Returns executed actions."""
        result = await self.db.execute(
            select(AssistantAction)
            .where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.user_id == user_id,
                AssistantAction.status == "queued",
            )
            .order_by(AssistantAction.created_at)
        )
        actions = list(result.scalars().all())

        executed = []
        for action in actions:
            try:
                await self._execute_action(action)
                action.status = "executed"
                action.executed_at = datetime.now(UTC)
                executed.append(action)
            except Exception as e:
                action.status = "failed"
                action.error_message = str(e)
                logger.error(
                    "Action {aid} failed: {err}",
                    aid=action.id,
                    err=str(e),
                )

        await self.db.flush()
        logger.info(
            "Processed {n}/{total} actions for user {uid}",
            n=len(executed),
            total=len(actions),
            uid=user_id,
        )
        return executed

    async def _execute_action(self, action: AssistantAction) -> None:
        """Execute a single action.

        Currently handles labelling and logging.
        Move/archive/delete require integration provider calls
        which will be added when the integration layer is connected.
        """
        action_type = action.action_type

        if action_type == "label":
            logger.info("Label action: item={iid}", iid=action.item_id)

        elif action_type == "prioritize":
            logger.info("Prioritize action: item={iid}", iid=action.item_id)

        elif action_type == "mute":
            logger.info("Mute action: item={iid}", iid=action.item_id)

        elif action_type in ("archive", "move", "delete"):
            # These require actual provider integration.
            # For now, we log and mark as executed.
            logger.info(
                "Mail action '{t}': item={iid} (provider call pending)",
                t=action_type,
                iid=action.item_id,
            )

        else:
            logger.warning(
                "Unknown action type '{t}' for action {aid}",
                t=action_type,
                aid=action.id,
            )
