"""LLM loop orchestration for the Assistant voice channel."""

import json

from loguru import logger

from app.assistant.context_view import build_context_summary
from app.assistant.tool_registry import AI_SUGGESTIONS_PROMPT, SYSTEM_PROMPT, TOOLS
from app.config import settings
from app.exceptions import ExternalServiceError


def resolve_assistant_llm_model(provider: str, model: str | None) -> str:
    """Return a provider-appropriate default model for the assistant."""
    if model:
        return model
    if provider == "anthropic":
        return settings.llm_model_content
    if provider == "openai":
        return settings.llm_model_analysis
    return settings.ollama_model


class VoiceLLMOrchestrator:
    """Run the chat-completions tool loop for voice interactions."""

    def __init__(self, *, llm_provider: str, llm_model: str | None) -> None:
        self.llm_provider = llm_provider
        self.llm_model = resolve_assistant_llm_model(llm_provider, llm_model)

    async def run_tool_loop(
        self,
        *,
        messages: list[dict],
        executor,
        context: dict,
        conversation_id: int,
        tenant_id: str,
        user_id: int,
        log_turn,
        ai_suggestions_enabled: bool = False,
    ) -> str:
        """Run LLM, execute tool calls, re-prompt until text response."""
        provider = self.llm_provider
        model = resolve_assistant_llm_model(provider, self.llm_model)

        logger.info("Voice LLM: provider={p} model={m}", p=provider, m=model)

        context_info = build_context_summary(context)
        system = SYSTEM_PROMPT
        if ai_suggestions_enabled:
            system += AI_SUGGESTIONS_PROMPT
        if context_info:
            system += f"\n\nAktueller Kontext:\n{context_info}"
        hint = self._build_confirmation_hint(context)
        if hint:
            system += f"\n\n{hint}"

        if provider == "anthropic":
            return await self._run_anthropic_tool_loop(
                model=model,
                system=system,
                messages=messages,
                executor=executor,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                user_id=user_id,
                log_turn=log_turn,
            )

        from openai import AsyncOpenAI

        if provider == "ollama":
            client = AsyncOpenAI(
                base_url=f"{settings.ollama_url}/v1",
                api_key="ollama",
            )
        elif provider == "openai":
            client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            client = AsyncOpenAI(
                base_url=f"{settings.ollama_url}/v1",
                api_key="ollama",
            )
            model = settings.ollama_model

        llm_messages = [{"role": "system", "content": system}, *messages]
        self._inject_confirmation_hint(llm_messages, context)

        for _ in range(5):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=llm_messages,
                    tools=TOOLS,
                    max_tokens=1024,
                    temperature=0.3,
                )
            except Exception as exc:
                logger.exception("LLM call failed: {err}", err=str(exc))
                raise ExternalServiceError("LLM", str(exc)) from exc

            choice = response.choices[0]
            if not choice.message.tool_calls:
                return choice.message.content or "Ich konnte keine Antwort generieren."

            llm_messages.append(choice.message.model_dump())
            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                result = await executor.execute(fn_name, fn_args)
                await log_turn(
                    tenant_id,
                    user_id,
                    conversation_id,
                    role="tool",
                    turn_type="tool_call",
                    tool_name=fn_name,
                    tool_args=fn_args,
                    tool_result_text=result,
                )
                llm_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "Ich konnte die Anfrage nicht vollstaendig bearbeiten. Bitte versuche es erneut."

    @staticmethod
    def _anthropic_tools() -> list[dict]:
        """Convert OpenAI-style function tools to Anthropic tools."""
        return [
            {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"],
            }
            for tool in TOOLS
        ]

    @staticmethod
    def _build_anthropic_messages(messages: list[dict]) -> list[dict]:
        """Convert simple chat history into Anthropic's message format."""
        anthropic_messages: list[dict] = []
        for message in messages:
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue
            anthropic_messages.append(
                {"role": role, "content": message.get("content") or ""}
            )
        return anthropic_messages

    async def _run_anthropic_tool_loop(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict],
        executor,
        conversation_id: int,
        tenant_id: str,
        user_id: int,
        log_turn,
    ) -> str:
        """Run Anthropic tool use loop for voice interactions."""
        if not settings.anthropic_api_key:
            raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        anthropic_messages = self._build_anthropic_messages(messages)

        for _ in range(5):
            try:
                response = await client.messages.create(
                    model=model,
                    max_tokens=1024,
                    temperature=0.3,
                    system=system,
                    messages=anthropic_messages,
                    tools=self._anthropic_tools(),
                )
            except Exception as exc:
                logger.exception("Anthropic LLM call failed: {err}", err=str(exc))
                raise ExternalServiceError("Anthropic", str(exc)) from exc

            assistant_content: list[dict] = []
            tool_uses: list[tuple[str, str, dict]] = []
            text_parts: list[str] = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    text = getattr(block, "text", "") or ""
                    text_parts.append(text)
                    assistant_content.append({"type": "text", "text": text})
                elif getattr(block, "type", None) == "tool_use":
                    fn_args = dict(getattr(block, "input", {}) or {})
                    tool_uses.append((block.id, block.name, fn_args))
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": fn_args,
                        }
                    )

            if not tool_uses:
                text = "".join(text_parts).strip()
                return text or "Ich konnte keine Antwort generieren."

            anthropic_messages.append(
                {"role": "assistant", "content": assistant_content}
            )

            tool_results = []
            for tool_use_id, fn_name, fn_args in tool_uses:
                result = await executor.execute(fn_name, fn_args)
                await log_turn(
                    tenant_id,
                    user_id,
                    conversation_id,
                    role="tool",
                    turn_type="tool_call",
                    tool_name=fn_name,
                    tool_args=fn_args,
                    tool_result_text=result,
                )
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result,
                    }
                )

            anthropic_messages.append({"role": "user", "content": tool_results})

        return "Ich konnte die Anfrage nicht vollstaendig bearbeiten. Bitte versuche es erneut."

    @staticmethod
    def _build_confirmation_hint(context: dict) -> str | None:
        """Build the strongest current confirmation hint."""
        pending = context.get("pending_confirmation")
        pending_reply = context.get("pending_reply")
        if pending:
            action = pending.get("action", "?")
            idx = pending.get("email_index", "")
            subject = pending.get("subject", pending.get("to", ""))
            tool_call = (
                "confirm_and_send(confirmed=true)"
                if action == "send_draft"
                else f"{action}(email_index={idx}, confirmed=true)"
            )
            return (
                f"[WICHTIG: Es wartet eine Bestaetigung. "
                f"Der User wurde gefragt ob {action} ausgefuehrt werden soll"
                f"{f' (Email {idx}: {subject})' if subject else ''}. "
                f"Wenn der User jetzt zustimmt (ja/ok/mach das), "
                f"rufe {tool_call} auf. "
                f"Bei Ablehnung sage 'Abgebrochen'.]"
            )
        if pending_reply:
            return (
                f"[WICHTIG: Entwurf bereit fuer {pending_reply.get('sender', '?')}. "
                f"Bei Zustimmung rufe confirm_and_send(confirmed=true) auf. "
                f"Bei Ablehnung sage 'Abgebrochen'.]"
            )
        return None

    @staticmethod
    def _inject_confirmation_hint(llm_messages: list[dict], context: dict) -> None:
        """Insert the strongest current confirmation hint before the last user turn."""
        hint = VoiceLLMOrchestrator._build_confirmation_hint(context)
        if hint:
            llm_messages.insert(-1, {"role": "system", "content": hint})
