"""KI-Chat for the email-template designer.

Pattern:
- Persistent chat history per template in ``email_template_chats``
- System prompt makes Claude an expert email-designer
- Custom tools: ``set_full_html``, ``apply_diff``, ``insert_image``,
  ``list_assets`` — Claude can directly modify the template HTML
- Each user turn writes one user-row + one (or more) assistant rows;
  tool results from the frontend write tool-rows back

The frontend manages the actual HTML (Vue refs), the backend just
stores the conversation + suggests changes via tool calls.
"""

from __future__ import annotations

from typing import Any

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.emailmarketing.asset_service import AssetService
from app.emailmarketing.models import EmailTemplate, EmailTemplateChat
from app.services.llm import get_model_for_class

SYSTEM_PROMPT = """Du bist ein erfahrener E-Mail-Template-Designer für ein deutsches B2B-Cold-Outreach-Tool.

PFLICHT in jeder Mail (DSGVO + UWG):
- Anrede mit {{first_name}}
- LLM-Body-Slot: {{llm_body}} — wird beim Versand pro Empfänger personalisiert
- Footer mit Impressum: {{impressum_block}}
- One-Click-Opt-Out-Link: <a href="{{unsubscribe_url}}">Abmelden</a>

VERFÜGBARE MERGE-TAGS:
- {{first_name}}, {{last_name}}, {{full_name}}, {{company_name}}, {{position}}
- {{llm_body}}, {{llm_subject}}
- {{tracking_hash}}
- {{tracking_link "/produkte"}} → wird beim Versand zu go4.energy/produkte?ref=…&utm_… expandiert
- {{unsubscribe_url}}, {{impressum_block}}

TECHNISCHE ANFORDERUNGEN:
- Max-width 600px (mobile-fähig)
- Inline-CSS (Outlook-Kompatibilität, kein <style>-Block, kein <script>)
- Tabelle-basiertes Layout für Cross-Client-Kompatibilität
- Web-Fonts vermeiden — Arial/Helvetica/sans-serif
- Bilder mit alt-Text + Fallback-Background-Color
- KEIN <html>, <head>, <body> wrapping — nur das innere Markup

VORGEHEN:
1. Wenn der User unklar ist, frage gezielt nach (Marken-Farben, Logo, Stil, CTA)
2. Verwende `list_assets` um zu sehen welche Bilder verfügbar sind
3. Bei Code-Änderungen: rufe `set_full_html` (komplett ersetzen) oder `apply_diff` (gezielt) auf
4. Erkläre kurz was du geändert hast und biete den nächsten sinnvollen Schritt an

Beispiel-Anfragen + dein Vorgehen:
- „Erstelle ein Cold-Outreach-Template" → Default-Template mit allen Pflicht-Elementen via set_full_html
- „Mach den Button blau" → apply_diff (nur Farbe ändern)
- „Füge mein Logo oben ein" → list_assets, dann insert_image am Anfang
"""


# Anthropic Tool-Definitions
TOOLS = [
    {
        "name": "set_full_html",
        "description": (
            "Replace the entire template HTML with new content. Use this when "
            "creating from scratch or doing major rewrites. Always include "
            "the required merge-tags ({{first_name}}, {{llm_body}}, "
            "{{unsubscribe_url}}, {{impressum_block}})."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "html": {
                    "type": "string",
                    "description": "The complete new HTML for the email body.",
                },
                "summary": {
                    "type": "string",
                    "description": "Short German description of what was created/changed.",
                },
            },
            "required": ["html", "summary"],
        },
    },
    {
        "name": "apply_diff",
        "description": (
            "Make a small targeted change to the existing HTML by replacing one "
            "exact substring with another. Use for small tweaks like color, "
            "text or attribute changes. The 'search' must be present exactly "
            "once in the HTML."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Exact substring to find (must be unique).",
                },
                "replace": {
                    "type": "string",
                    "description": "The replacement substring.",
                },
                "summary": {
                    "type": "string",
                    "description": "Short German description of the change.",
                },
            },
            "required": ["search", "replace", "summary"],
        },
    },
    {
        "name": "insert_image",
        "description": (
            "Insert an image at a specific anchor in the HTML. Use after "
            "list_assets to know the URL. The image should be embedded as "
            "an <img> with alt text and inline width."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Image URL (from asset library)"},
                "alt": {"type": "string", "description": "Alt text"},
                "width_px": {"type": "integer", "description": "Image width in pixels", "default": 200},
                "anchor": {
                    "type": "string",
                    "description": "Substring in the HTML before which to insert the image.",
                },
                "summary": {"type": "string"},
            },
            "required": ["url", "alt", "anchor", "summary"],
        },
    },
    {
        "name": "list_assets",
        "description": (
            "List the user's uploaded images / files (logos, photos, PDFs) "
            "they have available for this template. Returns name + URL + mime."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


class AiChatService:
    """Persistent chat with Claude for email template design."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._client: AsyncAnthropic | None = None

    def _client_or_raise(self) -> AsyncAnthropic:
        if self._client is None:
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY ist nicht gesetzt")
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def get_history(
        self, tenant_id: str, template_id: int
    ) -> list[EmailTemplateChat]:
        result = await self.db.execute(
            select(EmailTemplateChat)
            .where(EmailTemplateChat.tenant_id == tenant_id)
            .where(EmailTemplateChat.template_id == template_id)
            .order_by(EmailTemplateChat.created_at)
        )
        return list(result.scalars().all())

    async def clear_history(self, tenant_id: str, template_id: int) -> int:
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(EmailTemplateChat)
            .where(EmailTemplateChat.tenant_id == tenant_id)
            .where(EmailTemplateChat.template_id == template_id)
        )
        await self.db.flush()
        return result.rowcount or 0

    def _to_anthropic_messages(
        self,
        history: list[EmailTemplateChat],
        new_user_message: str,
        current_html: str | None,
    ) -> list[dict]:
        """Build Anthropic messages array from history + the new user message."""
        msgs: list[dict] = []
        for row in history:
            if row.role == "user":
                msgs.append({"role": "user", "content": row.content or ""})
            elif row.role == "assistant":
                # If the assistant called tools, we stored tool_calls; otherwise just text
                blocks: list[dict] = []
                if row.content:
                    blocks.append({"type": "text", "text": row.content})
                if row.tool_calls:
                    # tool_calls is a list of {id, name, input}
                    for tc in row.tool_calls:
                        blocks.append(
                            {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["name"],
                                "input": tc["input"],
                            }
                        )
                if blocks:
                    msgs.append({"role": "assistant", "content": blocks})
            elif row.role == "tool":
                # Each tool_result must be in a user message with type=tool_result
                msgs.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": row.tool_use_id,
                                "content": row.content or "",
                            }
                        ],
                    }
                )

        # Add new user turn — include current HTML as context if present
        user_text = new_user_message
        if current_html:
            user_text = (
                f"<aktuelles_html>\n{current_html}\n</aktuelles_html>\n\n"
                f"Anfrage:\n{new_user_message}"
            )
        msgs.append({"role": "user", "content": user_text})
        return msgs

    async def _execute_tool(
        self,
        tenant_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        current_html: str,
    ) -> tuple[str, str | None]:
        """Run a tool server-side where it makes sense.

        ``list_assets`` runs on the backend (tenant data).
        ``set_full_html`` / ``apply_diff`` / ``insert_image`` only update the
        HTML buffer — the new value is returned to the frontend.

        Returns (tool_result_text, new_html or None).
        """
        if tool_name == "list_assets":
            asset_service = AssetService(self.db)
            assets = await asset_service.list_assets(tenant_id, limit=50)
            if not assets:
                return ("Es sind aktuell keine Assets hochgeladen.", None)
            lines = ["Verfügbare Assets:"]
            for a in assets:
                lines.append(
                    f"- {a.original_filename} ({a.mime_type}, {a.size_bytes} B) → {a.url_path}"
                )
            return ("\n".join(lines), None)

        if tool_name == "set_full_html":
            new_html = tool_input.get("html", "")
            return (f"HTML ersetzt ({len(new_html)} Zeichen).", new_html)

        if tool_name == "apply_diff":
            search = tool_input.get("search", "")
            replace = tool_input.get("replace", "")
            count = current_html.count(search)
            if count == 0:
                return (
                    "Diff fehlgeschlagen: Suchtext nicht gefunden.",
                    None,
                )
            if count > 1:
                return (
                    f"Diff fehlgeschlagen: Suchtext kommt {count}-mal vor, muss eindeutig sein.",
                    None,
                )
            new_html = current_html.replace(search, replace, 1)
            return ("Diff angewandt.", new_html)

        if tool_name == "insert_image":
            url = tool_input.get("url", "")
            alt = tool_input.get("alt", "")
            width_px = int(tool_input.get("width_px", 200))
            anchor = tool_input.get("anchor", "")
            img_tag = (
                f'<img src="{url}" alt="{alt}" width="{width_px}" '
                f'style="display:block;max-width:{width_px}px;height:auto;border:0;">'
            )
            if anchor and anchor in current_html:
                new_html = current_html.replace(anchor, img_tag + anchor, 1)
                return ("Bild eingefügt.", new_html)
            # Fallback: append
            new_html = current_html + "\n" + img_tag
            return ("Bild am Ende angefügt (Anker nicht gefunden).", new_html)

        return (f"Unbekanntes Tool: {tool_name}", None)

    async def send_message(
        self,
        tenant_id: str,
        template_id: int,
        user_message: str,
        current_html: str | None = None,
    ) -> dict:
        """One round-trip: persist user message, call Claude, persist assistant
        + tool messages, return summary for frontend.
        """
        # Verify template belongs to tenant
        result = await self.db.execute(
            select(EmailTemplate)
            .where(EmailTemplate.id == template_id)
            .where(EmailTemplate.tenant_id == tenant_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            raise ValueError(f"Template {template_id} not found")

        history = await self.get_history(tenant_id, template_id)

        # Persist user message
        user_row = EmailTemplateChat(
            tenant_id=tenant_id,
            template_id=template_id,
            role="user",
            content=user_message,
        )
        self.db.add(user_row)
        await self.db.flush()

        client = self._client_or_raise()
        messages = self._to_anthropic_messages(history, user_message, current_html)

        # Resolve which Anthropic model to use — premium-class for the
        # creative template-design work (admin can override in Settings).
        model_id = await get_model_for_class("premium", self.db, tenant_id)

        # First Claude call
        response = await client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        running_html = current_html or ""
        all_tool_calls: list[dict] = []
        text_parts: list[str] = []

        # Loop: execute tools, send tool_results back, until no more tool_use
        while response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]
            for tb in text_blocks:
                text_parts.append(tb.text)

            # Persist assistant message with tool_calls
            assistant_text = "\n".join(b.text for b in text_blocks) or None
            tool_calls_json = [
                {"id": tu.id, "name": tu.name, "input": tu.input}
                for tu in tool_use_blocks
            ]
            self.db.add(
                EmailTemplateChat(
                    tenant_id=tenant_id,
                    template_id=template_id,
                    role="assistant",
                    content=assistant_text,
                    tool_calls=tool_calls_json,
                )
            )
            await self.db.flush()
            all_tool_calls.extend(tool_calls_json)

            # Execute tools and collect results
            tool_results = []
            for tu in tool_use_blocks:
                result_text, new_html = await self._execute_tool(
                    tenant_id, tu.name, tu.input, running_html
                )
                if new_html is not None:
                    running_html = new_html
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result_text,
                    }
                )
                # Persist tool result
                self.db.add(
                    EmailTemplateChat(
                        tenant_id=tenant_id,
                        template_id=template_id,
                        role="tool",
                        content=result_text,
                        tool_use_id=tu.id,
                    )
                )
            await self.db.flush()

            # Update messages array for next round
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = await client.messages.create(
                model=model_id,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

        # Final assistant message (no more tool_use)
        final_text_blocks = [b for b in response.content if b.type == "text"]
        final_text = "\n".join(b.text for b in final_text_blocks) or None
        if final_text:
            text_parts.append(final_text)

        assistant_row = EmailTemplateChat(
            tenant_id=tenant_id,
            template_id=template_id,
            role="assistant",
            content=final_text,
        )
        self.db.add(assistant_row)
        await self.db.flush()
        await self.db.refresh(assistant_row)

        return {
            "assistant_message": assistant_row,
            "tool_calls": all_tool_calls,
            "new_html": running_html if running_html != (current_html or "") else None,
        }
