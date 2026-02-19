"""Setup agent service - LLM with tool-calling loop for configuration."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.chat import ChatService
from app.setup.tools import SETUP_TOOLS, ToolExecutor

SKILLS_DIR = Path(__file__).parent / "skills"
MAX_HISTORY_MESSAGES = 20
MAX_TOOL_ROUNDS = 10


class SetupAgentService:
    """Setup agent with Anthropic tool-calling loop."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.chat = ChatService(db)
        self._skills_cache: str | None = None

    def _load_skills(self) -> str:
        """Load all skills markdown files, cached."""
        if self._skills_cache is not None:
            return self._skills_cache

        parts: list[str] = []
        if not SKILLS_DIR.exists():
            logger.warning("Skills-Verzeichnis nicht gefunden: {d}", d=str(SKILLS_DIR))
            self._skills_cache = ""
            return ""

        # Sort with _overview first
        files = sorted(
            SKILLS_DIR.glob("*.md"),
            key=lambda f: (not f.name.startswith("_"), f.name),
        )
        for f in files:
            content = f.read_text(encoding="utf-8")
            parts.append(f"--- {f.stem} ---\n{content}")

        self._skills_cache = "\n\n".join(parts)
        logger.info("Skills geladen: {count} Dateien", count=len(files))
        return self._skills_cache

    def _build_system_prompt(
        self, tenant_config: dict, setup_state: dict | None = None
    ) -> str:
        """Build the system prompt with skills and context."""
        company = tenant_config.get("COMPANY_NAME", "")
        tenant_id = tenant_config.get("TENANT_NAME", "")
        skills = self._load_skills()

        state_info = ""
        if setup_state and setup_state.get("modules"):
            lines = []
            for _key, mod in setup_state["modules"].items():
                status = "konfiguriert" if mod["configured"] else "offen"
                lines.append(f"  - {mod['label']}: {status} ({mod['details']})")
            state_info = "\n\n## Aktueller Setup-Status\n" + "\n".join(lines)

        return f"""Du bist der Setup-Assistent fuer go4-automate, eine Marketing-Automatisierungsplattform.
Tenant: {tenant_id} | Firma: {company or '(noch nicht konfiguriert)'}

## Deine Aufgabe
- Hilf dem Benutzer, die Plattform Schritt fuer Schritt einzurichten
- Stelle gezielte Fragen und konfiguriere dann automatisch per Tool-Aufrufe
- Schlage branchenspezifische Defaults vor
- Erklaere kurz was du tust, bevor du ein Tool aufrufst
- Fasse nach jeder Aenderung zusammen, was gesetzt wurde

## Regeln
- Antworte immer auf Deutsch
- Frage IMMER nach Bestaetigung bevor du etwas aenderst (z.B. "Soll ich das so setzen?")
- Schlage sinnvolle Defaults basierend auf der Branche vor
- Zeige nie API-Keys oder Tokens im Chat an
- Halte Antworten kompakt und uebersichtlich
- Wenn ein Modul fertig ist, frage ob das naechste konfiguriert werden soll
- Nutze die Tools aktiv um die Konfiguration zu lesen und zu aendern
{state_info}

## Wissensbasis (Skills)
{skills}"""

    async def get_setup_progress(self, tenant_id: str, tenant_config: dict) -> dict:
        """Get setup progress for the status endpoint."""
        executor = ToolExecutor(self.db, tenant_id, tenant_config)
        return await executor.execute("get_setup_progress", {})

    async def stream_response(
        self,
        tenant_id: str,
        conv_id: int,
        user_message: str,
        tenant_config: dict,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response with tool-calling loop as SSE events."""
        if not settings.anthropic_api_key:
            yield f"data: {json.dumps({'error': 'Anthropic API Key nicht konfiguriert'})}\n\n"
            return

        # Verify conversation
        conversation = await self.chat.get_conversation(tenant_id, conv_id)

        # Save user message
        await self.chat.add_message(conv_id, "user", user_message)
        await self.db.commit()

        # Auto-title
        if not conversation.title and len(conversation.messages) <= 1:
            title = user_message[:80]
            if len(user_message) > 80:
                title += "..."
            conversation.title = title
            await self.db.commit()

        # Load history
        history = await self.chat._load_history(conv_id)

        # Build system prompt with setup state
        executor = ToolExecutor(self.db, tenant_id, tenant_config)
        setup_state = await executor.execute("get_setup_progress", {})
        system_prompt = self._build_system_prompt(tenant_config, setup_state)

        # Tool-calling loop
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        messages = list(history)
        full_response = ""

        try:
            for _round in range(MAX_TOOL_ROUNDS):
                response = await client.messages.create(
                    model=settings.llm_model_content,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=SETUP_TOOLS,
                )

                # Process content blocks
                assistant_content = []
                for block in response.content:
                    if block.type == "text":
                        full_response += block.text
                        yield f"data: {json.dumps({'delta': block.text})}\n\n"
                        assistant_content.append(block)

                    elif block.type == "tool_use":
                        assistant_content.append(block)
                        # Notify frontend about tool call
                        yield f"data: {json.dumps({'tool_call': {'name': block.name, 'input': block.input}})}\n\n"

                        # Execute tool
                        result = await executor.execute(block.name, block.input)
                        await self.db.commit()

                        # Notify frontend about result
                        yield f"data: {json.dumps({'tool_result': {'name': block.name, 'result': result}})}\n\n"

                        # Build messages for next round
                        messages.append(
                            {"role": "assistant", "content": assistant_content}
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": block.id,
                                        "content": json.dumps(
                                            result, ensure_ascii=False
                                        ),
                                    }
                                ],
                            }
                        )
                        assistant_content = []

                # If no tool_use, we're done
                if response.stop_reason != "tool_use":
                    break

        except Exception as e:
            logger.exception("Setup-Agent Fehler: {err}", err=str(e))
            error_msg = "Es tut mir leid, es ist ein Fehler aufgetreten."
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            if not full_response:
                full_response = error_msg

        # Save complete assistant response
        assistant_msg = await self.chat.add_message(
            conv_id,
            "assistant",
            full_response,
            metadata={"provider": "anthropic", "type": "setup"},
        )
        await self.db.commit()

        yield f"data: {json.dumps({'done': True, 'message_id': assistant_msg.id})}\n\n"
