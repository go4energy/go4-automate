"""Assistant voice runtime support for conversation state and connection lookup."""

import inspect

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantConversation,
    AssistantConversationTurn,
    AssistantSource,
    IntegrationConnection,
)
from app.assistant.provider_router import require_supported_voice_provider
from app.exceptions import AppError


DEFAULT_VOICE_CONTEXT = {
    "messages": [],
    "email_list": [],
    "current_email_index": 0,
    "current_email_id": None,
    "connection_id": None,
}


class VoiceRuntimeSupport:
    """Persistence and connection helpers for the voice orchestrator."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def db_add(self, obj) -> None:
        """Support AsyncSession.add and AsyncMock.add in tests."""
        result = self.db.add(obj)
        if inspect.isawaitable(result):
            await result

    async def log_turn(
        self,
        tenant_id: str,
        user_id: int,
        conversation_id: int,
        *,
        role: str,
        content_text: str | None = None,
        turn_type: str = "message",
        tool_name: str | None = None,
        tool_args: dict | None = None,
        tool_result_text: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        turn = AssistantConversationTurn(
            tenant_id=tenant_id,
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            turn_type=turn_type,
            content_text=content_text,
            tool_name=tool_name,
            tool_args_json=tool_args,
            tool_result_text=tool_result_text,
            metadata_json=metadata,
        )
        await self.db_add(turn)
        await self.db.flush()

    async def get_or_create_conversation(
        self, tenant_id: str, user_id: int, conversation_id: int | None
    ) -> AssistantConversation:
        """Load existing conversation or create a fresh voice conversation."""
        if conversation_id:
            result = await self.db.execute(
                select(AssistantConversation).where(
                    AssistantConversation.id == conversation_id,
                    AssistantConversation.tenant_id == tenant_id,
                    AssistantConversation.user_id == user_id,
                )
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        conversation = AssistantConversation(
            tenant_id=tenant_id,
            user_id=user_id,
            channel="voice",
            state="active",
            context_json=dict(DEFAULT_VOICE_CONTEXT),
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_voice_connection(
        self, tenant_id: str, user_id: int
    ) -> tuple[str, str | None, int, str]:
        """Resolve the active voice source and ensure a usable access token."""
        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == tenant_id,
                AssistantSource.user_id == user_id,
                AssistantSource.voice_enabled.is_(True),
            )
            .order_by(AssistantSource.priority.desc())
            .limit(1)
        )
        source = result.scalar_one_or_none()

        if not source:
            result = await self.db.execute(
                select(AssistantSource)
                .where(
                    AssistantSource.tenant_id == tenant_id,
                    AssistantSource.user_id == user_id,
                )
                .order_by(AssistantSource.priority.desc())
                .limit(1)
            )
            source = result.scalar_one_or_none()

        if not source:
            raise AppError(
                "Kein Mailkonto verbunden. Bitte verbinde zuerst ein Konto.", 400
            )

        conn_result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id == source.connection_id,
            )
        )
        connection = conn_result.scalar_one_or_none()
        if not connection:
            raise AppError("Verbindung nicht gefunden.", 404)

        require_supported_voice_provider(connection.provider)

        from app.assistant.intake import AssistantIntakeService

        intake = AssistantIntakeService(self.db)
        access_token = await intake._ensure_access_token(connection)

        mailbox = None
        meta = connection.metadata_json or {}
        if meta.get("scope") == "shared_mailbox" and connection.mailbox_address:
            mailbox = connection.mailbox_address

        return access_token, mailbox, connection.id, connection.provider
