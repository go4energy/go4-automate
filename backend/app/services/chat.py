"""Chat service - conversation management with LLM streaming."""

import json
from collections.abc import AsyncGenerator

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.services.llm import LLMService

# System prompts per context type
CONTEXT_PROMPTS = {
    "onboarding": (
        "Du bist ein freundlicher Marketing-Berater fuer {{COMPANY_NAME}}. "
        "Stelle Onboarding-Fragen um das Unternehmen besser zu verstehen: "
        "1) Branche und Taetigkeitsfeld "
        "2) Zielgruppe und ideale Kunden "
        "3) Wichtige Themen und Schwerpunkte "
        "4) Wettbewerber und Alleinstellungsmerkmale "
        "5) Bevorzugte Social-Media-Plattformen. "
        "Gib konkrete, umsetzbare Empfehlungen basierend auf den Antworten."
    ),
    "research": (
        "Du hilfst {{COMPANY_NAME}} relevante Informationsquellen zu finden. "
        "Schlage RSS-Feeds, Branchenportale, Newsletter und Keywords vor "
        "basierend auf der Branche und den Interessen des Unternehmens. "
        "Gib konkrete URLs und Suchbegriffe an."
    ),
    "general": (
        "Du bist ein Marketing-Assistent fuer {{COMPANY_NAME}}. "
        "Hilf bei Content-Ideen, Marketing-Strategie, Kampagnenplanung "
        "und Konfiguration der Plattform. Antworte praeknant und hilfreich."
    ),
    "content": (
        "Du bist ein Content-Experte fuer {{COMPANY_NAME}}. "
        "Hilf bei der Erstellung, Verbesserung und Planung von Social-Media-Content. "
        "Gib konkrete Textvorschlaege, Hashtags und Timing-Empfehlungen."
    ),
}

MAX_HISTORY_MESSAGES = 20


class ChatService:
    """Chat service for conversation management and LLM streaming."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(
        self,
        tenant_id: str,
        title: str | None,
        context_type: str,
        context_data: dict | None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            tenant_id=tenant_id,
            title=title,
            context_type=context_type,
            context_data=context_data,
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        logger.info(
            "Conversation erstellt: id={id} type={ctx}",
            id=conversation.id,
            ctx=context_type,
        )
        return conversation

    async def list_conversations(
        self, tenant_id: str, status: str | None = None
    ) -> list[Conversation]:
        """List conversations for a tenant."""
        stmt = select(Conversation).where(Conversation.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(Conversation.updated_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation(self, tenant_id: str, conv_id: int) -> Conversation:
        """Get a conversation with messages."""
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conv_id, Conversation.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise NotFoundError("Conversation", conv_id)
        return conversation

    async def delete_conversation(self, tenant_id: str, conv_id: int) -> None:
        """Delete a conversation (cascade deletes messages)."""
        conversation = await self.get_conversation(tenant_id, conv_id)
        await self.db.delete(conversation)
        await self.db.flush()
        logger.info("Conversation geloescht: id={id}", id=conv_id)

    async def add_message(
        self, conv_id: int, role: str, content: str, metadata: dict | None = None
    ) -> ChatMessage:
        """Add a message to a conversation."""
        message = ChatMessage(
            conversation_id=conv_id,
            role=role,
            content=content,
            metadata_=metadata,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    def _build_system_prompt(self, context_type: str, tenant_config: dict) -> str:
        """Build system prompt with tenant context."""
        template = CONTEXT_PROMPTS.get(context_type, CONTEXT_PROMPTS["general"])
        company = tenant_config.get("COMPANY_NAME", "")
        return template.replace("{{COMPANY_NAME}}", company)

    async def _load_history(self, conv_id: int) -> list[dict]:
        """Load recent conversation history as message dicts."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(MAX_HISTORY_MESSAGES)
        )
        result = await self.db.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    async def stream_response(
        self,
        tenant_id: str,
        conv_id: int,
        user_message: str,
        tenant_config: dict,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response as SSE events."""
        # Verify conversation belongs to tenant
        conversation = await self.get_conversation(tenant_id, conv_id)

        # Save user message
        await self.add_message(conv_id, "user", user_message)
        await self.db.commit()

        # Auto-generate title from first message
        if not conversation.title and len(conversation.messages) <= 1:
            title = user_message[:80]
            if len(user_message) > 80:
                title += "..."
            conversation.title = title
            await self.db.commit()

        # Load history and build system prompt
        history = await self._load_history(conv_id)
        system_prompt = self._build_system_prompt(
            conversation.context_type, tenant_config
        )

        # Stream from LLM
        llm = LLMService(tenant_config)
        full_response = ""

        try:
            async for chunk in llm.stream_generate(
                system=system_prompt,
                messages=history,
                provider="anthropic",
            ):
                full_response += chunk
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        except Exception as e:
            logger.exception("LLM Stream-Fehler: {err}", err=str(e))
            error_msg = "Es tut mir leid, es ist ein Fehler aufgetreten. Bitte versuche es erneut."
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            full_response = error_msg

        # Save assistant response
        assistant_msg = await self.add_message(
            conv_id,
            "assistant",
            full_response,
            metadata={"provider": "anthropic"},
        )
        await self.db.commit()

        yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"
