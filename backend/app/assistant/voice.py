"""Assistant voice orchestration: conversation state, LLM loop, tool dispatch."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.assistant.context_view import build_voice_response_context
from app.assistant.llm_orchestrator import (
    VoiceLLMOrchestrator,
    resolve_assistant_llm_model,
)
from app.assistant.models import AssistantConversation
from app.assistant.tool_executor import VoiceToolExecutor
from app.assistant.voice_runtime import DEFAULT_VOICE_CONTEXT, VoiceRuntimeSupport


class VoiceService:
    """Orchestrate voice chat: LLM + tool calling + conversation state."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.runtime = VoiceRuntimeSupport(db)

    async def _db_add(self, obj) -> None:
        """Backward-compatible wrapper for runtime persistence helpers."""
        await self.runtime.db_add(obj)

    async def process_message(
        self,
        tenant_id: str,
        user_id: int,
        text: str,
        conversation_id: int | None = None,
    ) -> dict:
        """Process a user message, execute tools, return response."""
        # Load user profile for LLM provider/model
        from app.assistant.service import AssistantService

        profile = await AssistantService(self.db).get_or_create_profile(
            tenant_id, user_id
        )
        self._llm_provider = profile.llm_provider or "ollama"
        self._llm_model = resolve_assistant_llm_model(
            self._llm_provider, profile.llm_model
        )

        conversation = await self._get_or_create_conversation(
            tenant_id, user_id, conversation_id
        )
        context = conversation.context_json or dict(DEFAULT_VOICE_CONTEXT)

        (
            access_token,
            mailbox,
            connection_id,
            provider,
        ) = await self._get_voice_connection(tenant_id, user_id)
        context["connection_id"] = connection_id

        messages = context.get("messages", [])
        messages.append({"role": "user", "content": text})
        # Keep only last 6 messages (3 turns) to prevent history poisoning.
        # The LLM should decide based on current context + tools, not old messages.
        if len(messages) > 6:
            messages = messages[-6:]

        executor = VoiceToolExecutor(
            access_token=access_token,
            mailbox=mailbox,
            context=context,
            db=self.db,
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            conversation_id=conversation.id,
            connection_id=connection_id,
            llm_provider=self._llm_provider,
            llm_model=self._llm_model,
            skip_confirmation=bool(profile.skip_confirmation),
        )

        await self._log_turn(
            tenant_id,
            user_id,
            conversation.id,
            role="user",
            content_text=text,
            metadata={"channel": "voice"},
        )

        response_text = await self._llm_tool_loop(
            messages,
            executor,
            context,
            conversation.id,
            tenant_id,
            user_id,
            ai_suggestions_enabled=bool(profile.ai_suggestions_enabled),
        )

        messages.append({"role": "assistant", "content": response_text})
        await self._log_turn(
            tenant_id,
            user_id,
            conversation.id,
            role="assistant",
            content_text=response_text,
            metadata={"channel": "voice"},
        )

        context["messages"] = messages
        conversation.context_json = dict(context)
        flag_modified(conversation, "context_json")
        await self.db.flush()

        return {
            "text": response_text,
            "conversation_id": conversation.id,
            "context": build_voice_response_context(context),
        }

    async def _llm_tool_loop(
        self,
        messages: list[dict],
        executor: VoiceToolExecutor,
        context: dict,
        conversation_id: int,
        tenant_id: str,
        user_id: int,
        *,
        ai_suggestions_enabled: bool = False,
    ) -> str:
        """Backward-compatible wrapper around the dedicated LLM orchestrator."""
        orchestrator = VoiceLLMOrchestrator(
            llm_provider=self._llm_provider,
            llm_model=self._llm_model,
        )
        return await orchestrator.run_tool_loop(
            messages=messages,
            executor=executor,
            context=context,
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            log_turn=self._log_turn,
            ai_suggestions_enabled=ai_suggestions_enabled,
        )

    async def _log_turn(
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
        await self.runtime.log_turn(
            tenant_id,
            user_id,
            conversation_id,
            role=role,
            content_text=content_text,
            turn_type=turn_type,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result_text=tool_result_text,
            metadata=metadata,
        )

    async def _get_or_create_conversation(
        self, tenant_id: str, user_id: int, conversation_id: int | None
    ) -> AssistantConversation:
        """Backward-compatible wrapper for runtime conversation helpers."""
        return await self.runtime.get_or_create_conversation(
            tenant_id, user_id, conversation_id
        )

    async def _get_voice_connection(
        self, tenant_id: str, user_id: int
    ) -> tuple[str, str | None, int, str]:
        """Backward-compatible wrapper for runtime connection helpers."""
        return await self.runtime.get_voice_connection(tenant_id, user_id)
