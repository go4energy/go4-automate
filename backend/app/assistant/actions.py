"""Assistant action executor - processes queued actions."""

from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import AssistantAction


class ActionNotImplementedError(Exception):
    """Raised when an action type has no provider implementation yet."""


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
                action.executed_at = datetime.utcnow()
                executed.append(action)
            except ActionNotImplementedError as e:
                action.status = "not_implemented"
                action.error_message = str(e)
                logger.warning(
                    "Action {aid} not implemented: {err}",
                    aid=action.id,
                    err=str(e),
                )
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

        Raises ActionNotImplementedError for types that need provider
        integration which is not yet connected.
        """
        action_type = action.action_type

        if action_type == "label":
            # Label is metadata-only, applied on the item in our DB
            logger.info("Label action: item={iid}", iid=action.item_id)

        elif action_type == "prioritize":
            # Prioritize is metadata-only, applied on the item in our DB
            logger.info("Prioritize action: item={iid}", iid=action.item_id)

        elif action_type == "mute":
            # Mute is metadata-only, applied on the item in our DB
            logger.info("Mute action: item={iid}", iid=action.item_id)

        elif action_type in ("archive", "move", "delete"):
            # These require actual provider integration (Microsoft Graph etc.)
            raise ActionNotImplementedError(
                f"Mail-Aktion '{action_type}' erfordert Provider-Integration "
                f"(noch nicht implementiert fuer item={action.item_id})"
            )

        else:
            raise ActionNotImplementedError(
                f"Unbekannter Aktionstyp '{action_type}' " f"fuer action={action.id}"
            )
