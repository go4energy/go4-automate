"""Assistant voice tool execution against provider and persistence layers."""

import inspect
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.llm_orchestrator import resolve_assistant_llm_model
from app.assistant.models import (
    AssistantDraft,
    AssistantPendingIntent,
    AssistantSource,
    IntegrationConnection,
)
from app.assistant.policy import (
    clear_pending_draft_context,
    clear_pending_intent_context,
    set_pending_draft_context,
    set_pending_intent_context,
)
from app.assistant.provider_router import SUPPORTED_VOICE_PROVIDERS
from app.assistant.service import AssistantService
from app.assistant.time_utils import utc_in_naive, utc_now_naive
from app.config import settings
from app.exceptions import AppError, ExternalServiceError, ValidationError


class VoiceToolExecutor:
    """Execute tool calls against Microsoft Graph and local DB."""

    def __init__(
        self,
        access_token: str,
        mailbox: str | None,
        context: dict,
        db: AsyncSession,
        tenant_id: str,
        user_id: int,
        provider: str,
        conversation_id: int | None = None,
        connection_id: int | None = None,
        llm_provider: str = "ollama",
        llm_model: str | None = None,
        skip_confirmation: bool = False,
    ) -> None:
        self.access_token = access_token
        self.mailbox = mailbox
        self.context = context
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.provider = provider
        self.conversation_id = conversation_id
        self.connection_id = connection_id
        self.skip_confirmation = skip_confirmation
        self.llm_provider = llm_provider
        self.llm_model = resolve_assistant_llm_model(llm_provider, llm_model)

    async def execute(self, tool_name: str, args: dict) -> str:
        """Execute a tool and return result as string."""
        logger.info("Tool call: {name} args={args}", name=tool_name, args=args)
        handler = getattr(self, f"_tool_{tool_name}", None)
        if not handler:
            return f"Unbekanntes Tool: {tool_name}"
        try:
            result = await handler(args)
            logger.info("Tool result: {name} → {r}", name=tool_name, r=result[:200])
            return result
        except ExternalServiceError as e:
            logger.error(
                "Tool {name} ExternalServiceError: {err}", name=tool_name, err=e.message
            )
            return f"Fehler: {e.message}"
        except Exception as e:
            logger.exception("Tool {name} exception: {err}", name=tool_name, err=str(e))
            return f"Fehler bei {tool_name}: {str(e)[:200]}"

    def _check_provider(self) -> str | None:
        """Return error message if provider is not supported."""
        if self.provider not in SUPPORTED_VOICE_PROVIDERS:
            return (
                f"Provider '{self.provider}' wird fuer diese Aktion noch nicht "
                f"unterstuetzt. Aktuell nur Microsoft Graph."
            )
        return None

    def _get_graph_client(self, access_token: str | None = None):
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        return MicrosoftGraphClient(access_token or self.access_token)

    def _get_email_mailbox(self, index: int) -> str | None:
        """Get email mailbox from context by 1-based index."""
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            return email_list[index - 1].get("mailbox")
        return None

    def _get_email_id(self, index: int) -> str | None:
        """Get email ID from context by 1-based index."""
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            return email_list[index - 1].get("id")
        return None

    def _get_email_subject(self, index: int) -> str:
        """Get email subject from context by 1-based index."""
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            return email_list[index - 1].get("subject", "(kein Betreff)")
        return "(unbekannt)"

    def _get_email_folder_id(self, index: int) -> str | None:
        """Get current folder ID from context by 1-based index."""
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            return email_list[index - 1].get("parent_folder_id")
        return None

    def _get_email_thread_id(self, index: int) -> str | None:
        """Get current thread ID from context by 1-based index."""
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            return email_list[index - 1].get("thread_id")
        return None

    def _resolve_email_index_for_action(self, args: dict) -> int:
        """Prefer the currently focused email for generic follow-up actions.

        Anthropic sometimes emits `email_index=1` for commands like
        "verschiebe nach TEMP", even when the user is currently on email 2+.
        If there is an active current email and the requested index points to a
        different message, treat the current focus as authoritative unless the
        model clearly targeted a different non-default index.
        """
        email_list = self.context.get("email_list", [])
        current_index = self.context.get("current_email_index")
        current_email_id = self.context.get("current_email_id")

        if not email_list or not current_index or not (1 <= current_index <= len(email_list)):
            return args.get("email_index", 1)

        if "email_index" not in args or args.get("email_index") is None:
            return current_index

        requested_index = args.get("email_index", current_index)
        if not isinstance(requested_index, int):
            try:
                requested_index = int(requested_index)
            except (TypeError, ValueError):
                return current_index

        if not (1 <= requested_index <= len(email_list)):
            return current_index

        requested_email_id = self._get_email_id(requested_index)
        if (
            requested_index == 1
            and current_index != 1
            and current_email_id
            and requested_email_id != current_email_id
        ):
            return current_index

        return requested_index

    def _get_event(self, index: int) -> dict | None:
        """Get event from context by 1-based index."""
        events = self.context.get("calendar_events", [])
        if 1 <= index <= len(events):
            return events[index - 1]
        return None

    async def _fetch_email_text_for_summary(
        self, email_id: str, mailbox: str | None = None
    ) -> str | None:
        """Fetch richer message text for voice summaries."""
        err = self._check_provider()
        if err:
            return None

        _cid, token, scoped_mailbox = await self._get_scoped_connection(mailbox=mailbox)
        client = (
            self._get_graph_client()
            if token == self.access_token
            else self._get_graph_client(token)
        )
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/messages/{email_id}",
            params={"$select": "body,bodyPreview"},
        )
        body = ((data.get("body") or {}).get("content") or "").strip()
        preview = (data.get("bodyPreview") or "").strip()
        text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            return text[:4000]
        if preview:
            return preview[:1000]
        return None

    async def _summarize_email_for_voice(self, email: dict) -> str:
        """Build a short voice-friendly summary with graceful fallbacks."""
        if email.get("summary"):
            return email["summary"]

        base_text = ""
        if email.get("id"):
            try:
                base_text = (
                    await self._fetch_email_text_for_summary(
                        email["id"], mailbox=email.get("mailbox")
                    )
                    or ""
                )
            except Exception:
                logger.exception("Email summary fetch failed")
        if not base_text:
            base_text = (email.get("snippet") or "").strip()
        if not base_text:
            return "Keine Kurzfassung verfuegbar."

        provider = self.llm_provider
        model = resolve_assistant_llm_model(provider, self.llm_model)
        if provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ExternalServiceError("Anthropic", "API Key nicht konfiguriert")

            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        elif provider == "ollama":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=f"{settings.ollama_url}/v1",
                api_key="ollama",
            )
        elif provider == "openai":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.openai_api_key)
        else:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                base_url=f"{settings.ollama_url}/v1",
                api_key="ollama",
            )
            model = settings.ollama_model

        system = (
            "Du fasst E-Mails fuer Sprachausgabe zusammen. "
            "Antworte auf Deutsch in genau 1 bis 2 kurzen Saetzen. "
            "Keine Halluzinationen, keine Begruessung, keine Meta-Erklaerungen."
        )
        prompt = (
            f"Absender: {email.get('sender') or 'Unbekannt'}\n"
            f"Betreff: {email.get('subject') or '(kein Betreff)'}\n"
            f"Inhalt:\n{base_text[:2500]}"
        )
        try:
            if provider == "anthropic":
                response = await client.messages.create(
                    model=model,
                    max_tokens=120,
                    temperature=0.2,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                summary = "".join(
                    block.text
                    for block in response.content
                    if getattr(block, "type", None) == "text"
                ).strip()
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=120,
                    temperature=0.2,
                )
                summary = (response.choices[0].message.content or "").strip()
        except Exception:
            logger.exception("Email summary generation failed")
            summary = ""

        if not summary:
            summary = base_text[:220]
        email["summary"] = summary
        return summary

    async def _summarize_thread_for_voice(self, messages: list[dict]) -> str:
        """Build a short voice-friendly summary for a thread."""
        if not messages:
            return "Keine Thread-Zusammenfassung verfuegbar."

        first = messages[0]
        last = messages[-1]
        subject = first.get("subject") or last.get("subject") or "(kein Betreff)"
        first_sender = first.get("sender") or "Unbekannt"
        last_sender = last.get("sender") or "Unbekannt"
        if len(messages) == 1:
            return f"Eine Nachricht zu '{subject}' von {first_sender}."
        return (
            f"Thread zu '{subject}' mit {len(messages)} Nachrichten. "
            f"Er begann mit {first_sender} und zuletzt antwortete {last_sender}."
        )

    async def _db_add(self, obj) -> None:
        """Support AsyncSession.add and AsyncMock.add in tests."""
        result = self.db.add(obj)
        if inspect.isawaitable(result):
            await result

    async def _create_pending_intent(
        self,
        intent_type: str,
        *,
        connection_id: int | None = None,
        target_type: str | None = None,
        target_ref: dict | None = None,
        payload: dict | None = None,
        metadata: dict | None = None,
    ) -> AssistantPendingIntent:
        intent = AssistantPendingIntent(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            connection_id=connection_id or self.connection_id,
            intent_type=intent_type,
            status="awaiting_confirmation",
            target_type=target_type,
            target_ref_json=target_ref,
            payload_json=payload,
            confirmation_token=uuid4().hex,
            expires_at=utc_in_naive(minutes=15),
            metadata_json=metadata,
        )
        await self._db_add(intent)
        await self.db.flush()
        set_pending_intent_context(
            self.context,
            intent.id,
            intent_type,
            target_ref=target_ref,
            payload=payload,
        )
        return intent

    async def _get_pending_intent(self, action: str) -> AssistantPendingIntent | None:
        pending = self.context.get("pending_confirmation") or {}
        pending_id = self.context.get("pending_intent_id") or pending.get("id")
        if not pending_id:
            if pending.get("action") != action:
                return None
            return AssistantPendingIntent(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                connection_id=self.connection_id,
                intent_type=action,
                status="awaiting_confirmation",
                target_ref_json=pending,
                payload_json=pending,
            )

        result = await self.db.execute(
            select(AssistantPendingIntent).where(
                AssistantPendingIntent.id == pending_id,
                AssistantPendingIntent.tenant_id == self.tenant_id,
                AssistantPendingIntent.user_id == self.user_id,
            )
        )
        intent = result.scalar_one_or_none()
        if not intent or intent.intent_type != action:
            return None
        if intent.status != "awaiting_confirmation":
            return None
        if intent.expires_at and intent.expires_at < utc_now_naive():
            intent.status = "expired"
            await self.db.flush()
            return None
        return intent

    async def _create_draft(
        self,
        *,
        connection_id: int | None = None,
        draft_type: str,
        target_external_id: str | None,
        subject: str | None,
        body_text: str,
        recipients: list[str] | None,
        metadata: dict | None = None,
    ) -> AssistantDraft:
        draft = AssistantDraft(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            connection_id=connection_id or self.connection_id,
            draft_type=draft_type,
            status="draft",
            target_external_id=target_external_id,
            subject=subject,
            body_text=body_text,
            body_html=f"<p>{body_text}</p>",
            to_recipients_json={"items": recipients or []},
            metadata_json=metadata,
        )
        await self._db_add(draft)
        await self.db.flush()
        set_pending_draft_context(
            self.context,
            draft.id,
            sender=recipients[0] if recipients else "",
            subject=subject or "",
            reply_text=body_text,
            email_id=target_external_id,
            draft_type=draft_type,
        )
        set_pending_intent_context(
            self.context,
            None,
            "send_draft",
            target_ref={
                "draft_id": draft.id,
                "subject": subject or "",
                "to": recipients[0] if recipients else "",
            },
        )
        return draft

    async def _get_pending_draft(self) -> AssistantDraft | None:
        pending = self.context.get("pending_reply") or {}
        draft_id = self.context.get("pending_draft_id") or pending.get("id")
        if not draft_id:
            if not pending.get("reply_text"):
                return None
            recipients = [pending["sender"]] if pending.get("sender") else []
            return AssistantDraft(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                connection_id=self.connection_id,
                draft_type="reply",
                status="draft",
                target_external_id=pending.get("email_id"),
                subject=pending.get("subject"),
                body_text=pending.get("reply_text"),
                body_html=f"<p>{pending.get('reply_text', '')}</p>",
                to_recipients_json={"items": recipients},
            )
        result = await self.db.execute(
            select(AssistantDraft).where(
                AssistantDraft.id == draft_id,
                AssistantDraft.tenant_id == self.tenant_id,
                AssistantDraft.user_id == self.user_id,
            )
        )
        draft = result.scalar_one_or_none()
        if not draft or draft.status != "draft":
            return None
        return draft

    def _resolve_mailbox_scope(
        self,
        mailbox: str | None = None,
        *,
        all_mailboxes: bool = False,
    ) -> str | None:
        """Resolve explicit mailbox or fall back to the current active mailbox scope."""
        if all_mailboxes:
            return None
        if mailbox:
            return mailbox
        return self.context.get("active_mailbox")

    def _resolve_folder_scope(self, folder: str | None = None) -> str | None:
        """Resolve explicit folder or fall back to the active folder scope."""
        if folder:
            return folder
        return self.context.get("active_folder_name")

    async def _get_scoped_connection(
        self,
        *,
        mailbox: str | None = None,
        index: int | None = None,
    ) -> tuple[int | None, str, str | None]:
        """Resolve the effective connection/token/mailbox for mailbox-scoped operations."""
        effective_mailbox = self._resolve_mailbox_scope(mailbox)
        if index is not None:
            effective_mailbox = self._get_email_mailbox(index) or effective_mailbox

        if not effective_mailbox or effective_mailbox == self.mailbox:
            return self.connection_id, self.access_token, self.mailbox

        connections = await self._list_voice_connections(mailbox=effective_mailbox)
        if not connections:
            return self.connection_id, self.access_token, self.mailbox
        conn, token, mailbox_name = connections[0]
        return conn.id, token, mailbox_name

    async def _list_voice_connections(
        self,
        *,
        mailbox: str | None = None,
        all_mailboxes: bool = False,
    ) -> list[tuple[IntegrationConnection, str, str | None]]:
        mailbox = self._resolve_mailbox_scope(mailbox, all_mailboxes=all_mailboxes)
        from app.assistant.intake import AssistantIntakeService

        result = await self.db.execute(
            select(AssistantSource)
            .where(
                AssistantSource.tenant_id == self.tenant_id,
                AssistantSource.user_id == self.user_id,
            )
            .order_by(AssistantSource.priority.desc(), AssistantSource.id.asc())
        )
        sources = list(result.scalars().all())
        if not sources:
            return []

        connection_ids = [source.connection_id for source in sources]
        conn_result = await self.db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.id.in_(connection_ids),
                IntegrationConnection.provider.in_(SUPPORTED_VOICE_PROVIDERS),
            )
        )
        connections = {conn.id: conn for conn in conn_result.scalars().all()}

        selected = []
        for source in sources:
            conn = connections.get(source.connection_id)
            if not conn:
                continue
            effective_mailbox = conn.mailbox_address or conn.connected_email
            if mailbox and effective_mailbox != mailbox:
                continue
            selected.append(conn)
            if mailbox or not all_mailboxes:
                break

        intake = AssistantIntakeService(self.db)
        resolved = []
        for conn in selected:
            token = await intake._ensure_access_token(conn)
            resolved.append((conn, token, conn.mailbox_address or conn.connected_email))
        return resolved

    async def _fetch_mailbox_messages(
        self,
        token: str,
        mailbox: str | None,
        *,
        unread_only: bool = False,
        limit: int = 20,
    ):
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.microsoft_graph.mail_read import (
            MicrosoftGraphMailReadProvider,
        )

        client = MicrosoftGraphClient(token)
        provider = MicrosoftGraphMailReadProvider(client)
        return await provider.list_messages(
            mailbox=mailbox,
            unread_only=unread_only,
            limit=limit,
        )

    async def _fetch_folder_messages(
        self,
        token: str,
        mailbox: str | None,
        *,
        folder_name: str,
        unread_only: bool = False,
        limit: int = 20,
    ):
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.types import MailMessageRef

        client = MicrosoftGraphClient(token)
        folder_id = await self._resolve_folder_id_for_mailbox(token, mailbox, folder_name)
        if not folder_id:
            return []

        principal = f"users/{mailbox}" if mailbox else "me"
        params = {
            "$top": max(1, min(limit, 100)),
            "$orderby": "receivedDateTime desc",
            "$select": ",".join(
                [
                    "id",
                    "conversationId",
                    "subject",
                    "from",
                    "receivedDateTime",
                    "isRead",
                    "bodyPreview",
                    "parentFolderId",
                    "hasAttachments",
                ]
            ),
        }
        if unread_only:
            params["$filter"] = "isRead eq false"
        payload = await client.get(
            f"{principal}/mailFolders/{folder_id}/messages",
            params=params,
        )
        messages = []
        for item in payload.get("value", []):
            sender = (item.get("from") or {}).get("emailAddress") or {}
            received_at = item.get("receivedDateTime")
            messages.append(
                MailMessageRef(
                    provider_message_id=item["id"],
                    subject=item.get("subject") or "",
                    from_email=sender.get("address"),
                    received_at=datetime.fromisoformat(
                        received_at.replace("Z", "+00:00")
                    )
                    if received_at
                    else None,
                    is_unread=not bool(item.get("isRead", False)),
                    snippet=item.get("bodyPreview"),
                    thread_id=item.get("conversationId"),
                    raw=item,
                )
            )
        return messages

    async def _fetch_calendar_events(
        self,
        token: str,
        mailbox: str | None,
        *,
        limit: int = 10,
    ):
        from app.integrations.microsoft_graph.calendar import (
            MicrosoftGraphCalendarProvider,
        )
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        provider = MicrosoftGraphCalendarProvider(client)
        return await provider.list_events(mailbox=mailbox, limit=limit)

    async def _find_last_meeting_timestamp(
        self,
        reference: str,
        *,
        mailbox: str | None = None,
        all_mailboxes: bool = False,
    ) -> str | None:
        reference_lc = reference.strip().lower()
        if not reference_lc:
            return None

        connections = await self._list_voice_connections(
            mailbox=mailbox,
            all_mailboxes=all_mailboxes,
        )
        if not connections:
            return None

        now = datetime.now(UTC)
        latest = None
        for _conn, token, mailbox_name in connections:
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient

            client = MicrosoftGraphClient(token)
            principal = f"users/{mailbox_name}" if mailbox_name else "me"
            data = await client.get(
                f"{principal}/events",
                params={
                    "$top": "25",
                    "$orderby": "end/dateTime desc",
                    "$select": "id,subject,start,end,organizer,attendees,location",
                },
            )
            for item in data.get("value", []):
                end_raw = ((item.get("end") or {}).get("dateTime")) or ""
                try:
                    end_dt = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if end_dt > now:
                    continue

                subject = (item.get("subject") or "").lower()
                organizer = (
                    (item.get("organizer") or {})
                    .get("emailAddress", {})
                    .get("address", "")
                    .lower()
                )
                attendees = " ".join(
                    (
                        (att.get("emailAddress") or {}).get("address", "")
                        + " "
                        + (att.get("emailAddress") or {}).get("name", "")
                    ).lower()
                    for att in (item.get("attendees") or [])
                )
                haystack = f"{subject} {organizer} {attendees}"
                if reference_lc not in haystack:
                    continue
                if latest is None or end_dt > latest:
                    latest = end_dt

        return latest.isoformat() if latest else None

    async def _load_cleanup_rules(self):
        from app.assistant.models import AssistantRule

        result = await self.db.execute(
            select(AssistantRule)
            .where(
                AssistantRule.tenant_id == self.tenant_id,
                AssistantRule.user_id == self.user_id,
                AssistantRule.enabled.is_(True),
            )
            .order_by(AssistantRule.priority.desc(), AssistantRule.id.asc())
        )
        return list(result.scalars().all())

    def _rule_matches_message(self, rule, message, mailbox: str | None) -> bool:
        criteria = rule.match_criteria_json or {}
        if not criteria:
            return False
        title = (message.subject or "").lower()
        sender = (message.from_email or "").lower()
        snippet = (message.snippet or "").lower()

        if (
            "sender_domain" in criteria
            and criteria["sender_domain"].lower() not in sender
        ):
            return False
        if (
            "sender_contains" in criteria
            and criteria["sender_contains"].lower() not in sender
        ):
            return False
        if (
            "subject_contains" in criteria
            and criteria["subject_contains"].lower() not in title
        ):
            return False
        if "subject_regex" in criteria:
            try:
                if not re.search(
                    criteria["subject_regex"], message.subject or "", re.IGNORECASE
                ):
                    return False
            except re.error:
                return False
        if "keywords" in criteria:
            keywords = [k.lower() for k in criteria["keywords"]]
            if not any(kw in title or kw in snippet for kw in keywords):
                return False
        return not (
            "mailbox" in criteria
            and (mailbox or "").lower() != criteria["mailbox"].lower()
        )

    async def _build_cleanup_preview(
        self,
        *,
        mailbox: str | None = None,
        all_mailboxes: bool = False,
        unread_only: bool = True,
        limit_per_mailbox: int = 30,
    ) -> dict:
        rules = await self._load_cleanup_rules()
        if not rules:
            return {"operations": [], "summary": "Keine aktiven Regeln vorhanden."}

        connections = await self._list_voice_connections(
            mailbox=mailbox,
            all_mailboxes=all_mailboxes,
        )
        if not connections:
            return {"operations": [], "summary": "Kein passendes Postfach gefunden."}

        operations = []
        counts = {}
        for _conn, token, mailbox_name in connections:
            folder_cache = {}
            messages = await self._fetch_mailbox_messages(
                token,
                mailbox_name,
                unread_only=unread_only,
                limit=limit_per_mailbox,
            )
            for message in messages:
                for rule in rules:
                    if not self._rule_matches_message(rule, message, mailbox_name):
                        continue
                    action_type = rule.action_type
                    if action_type not in {"move", "delete", "archive"}:
                        break
                    effective_action = (
                        "move" if action_type in {"move", "archive"} else "delete"
                    )
                    folder = (rule.action_payload_json or {}).get("target", "Archive")
                    folder_id = None
                    if effective_action == "move":
                        folder_id = folder_cache.get(folder.lower())
                        if not folder_id:
                            folder_id = await self._resolve_folder_id_for_mailbox(
                                token, mailbox_name, folder
                            )
                            if folder_id:
                                folder_cache[folder.lower()] = folder_id
                            else:
                                break
                    operations.append(
                        {
                            "mailbox": mailbox_name,
                            "email_id": message.provider_message_id,
                            "subject": message.subject,
                            "sender": message.from_email,
                            "action": effective_action,
                            "folder": folder if effective_action == "move" else None,
                            "folder_id": folder_id,
                            "original_folder_id": (message.raw or {}).get(
                                "parentFolderId"
                            ),
                            "original_folder_name": None,
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                        }
                    )
                    key = f"{mailbox_name}:{effective_action}:{folder}"
                    counts[key] = counts.get(key, 0) + 1
                    break

        if not operations:
            return {
                "operations": [],
                "summary": "Aktuell gibt es keine ungelesenen Emails, die durch vorhandene Regeln bereinigt werden koennten.",
            }

        lines = [f"{len(operations)} Emails koennten bereinigt werden:"]
        for key, count in counts.items():
            mailbox_name, action, folder = key.split(":", 2)
            if action == "move":
                lines.append(f"- {mailbox_name}: {count}x verschieben nach {folder}")
            else:
                lines.append(f"- {mailbox_name}: {count}x loeschen")
        return {"operations": operations, "summary": "\n".join(lines)}

    async def _resolve_folder_id_for_mailbox(
        self, token: str, mailbox: str | None, folder_name: str
    ) -> str | None:
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        principal = f"users/{mailbox}" if mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={"$select": "id,displayName", "$top": "100"},
        )
        for folder in data.get("value", []):
            if folder.get("displayName", "").lower() == folder_name.lower():
                return folder.get("id")
        return None

    def _normalize_since_filter(self, since: str | None) -> str | None:
        """Normalize simple German relative date phrases to ISO timestamps."""
        if not since:
            return None
        value = since.strip()
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass

        now = datetime.now().astimezone()
        lowered = value.lower()
        day_map = {
            "montag": 0,
            "dienstag": 1,
            "mittwoch": 2,
            "donnerstag": 3,
            "freitag": 4,
            "samstag": 5,
            "sonntag": 6,
        }

        if lowered == "heute":
            return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if lowered == "gestern":
            dt = now - timedelta(days=1)
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        match = re.search(
            r"(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)"
            r"(?:\s+(frueh|früh|morgen|vormittag|mittag|nachmittag|abend))?",
            lowered,
        )
        if not match:
            return None

        weekday = day_map[match.group(1)]
        modifier = match.group(2) or ""
        days_back = (now.weekday() - weekday) % 7
        target = now - timedelta(days=days_back)
        if days_back == 0 and "seit" in lowered:
            target = now

        hour = 0
        if modifier in {"frueh", "früh", "morgen"}:
            hour = 6
        elif modifier == "vormittag":
            hour = 9
        elif modifier == "mittag":
            hour = 12
        elif modifier == "nachmittag":
            hour = 15
        elif modifier == "abend":
            hour = 18

        return target.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()

    async def _tool_list_emails(self, args: dict) -> str:
        err = self._check_provider()
        if err:
            return err

        _cid, token, scoped_mailbox = await self._get_scoped_connection()
        client = (
            self._get_graph_client()
            if token == self.access_token
            else self._get_graph_client(token)
        )
        limit = min(max(args.get("limit", 5), 1), 10)
        unread_only = args.get("unread_only", False)
        folder = self._resolve_folder_scope(args.get("folder"))

        if folder:
            folder_id = self.context.get("active_folder_id")
            if not folder_id or self.context.get("active_folder_name") != folder:
                folder_id = await self._resolve_folder_id(folder)
            if not folder_id:
                return f"Ordner '{folder}' wurde nicht gefunden."
            self.context["active_folder_name"] = folder
            self.context["active_folder_id"] = folder_id
            principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
            params = {
                "$top": str(limit),
                "$orderby": "receivedDateTime desc",
                "$select": ",".join(
                    [
                        "id",
                        "conversationId",
                        "subject",
                        "from",
                        "receivedDateTime",
                        "isRead",
                        "bodyPreview",
                        "parentFolderId",
                        "hasAttachments",
                    ]
                ),
            }
            if unread_only:
                params["$filter"] = "isRead eq false"
            data = await client.get(
                f"{principal}/mailFolders/{folder_id}/messages",
                params=params,
            )
            items = data.get("value", [])
            messages = []
            for item in items:
                sender = (item.get("from") or {}).get("emailAddress") or {}
                received_at = item.get("receivedDateTime")
                messages.append(
                    {
                        "id": item.get("id"),
                        "subject": item.get("subject") or "",
                        "sender": sender.get("address"),
                        "is_unread": not bool(item.get("isRead", False)),
                        "snippet": item.get("bodyPreview"),
                        "received_at": received_at,
                        "parent_folder_id": item.get("parentFolderId"),
                        "has_attachments": bool(item.get("hasAttachments", False)),
                        "thread_id": item.get("conversationId"),
                        "mailbox": scoped_mailbox,
                    }
                )
        else:
            # Default: nur Inbox lesen, nicht alle Ordner
            principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
            params = {
                "$top": str(limit),
                "$orderby": "receivedDateTime desc",
                "$select": ",".join(
                    [
                        "id",
                        "conversationId",
                        "subject",
                        "from",
                        "receivedDateTime",
                        "isRead",
                        "bodyPreview",
                        "parentFolderId",
                        "hasAttachments",
                    ]
                ),
            }
            if unread_only:
                params["$filter"] = "isRead eq false"
            data = await client.get(
                f"{principal}/mailFolders/Inbox/messages",
                params=params,
            )
            items = data.get("value", [])
            provider_messages = []
            for item in items:
                sender = (item.get("from") or {}).get("emailAddress") or {}
                received_at = item.get("receivedDateTime")
                from app.integrations.types import MailMessageRef

                provider_messages.append(
                    MailMessageRef(
                        provider_message_id=item.get("id", ""),
                        subject=item.get("subject") or "",
                        from_email=sender.get("address"),
                        received_at=datetime.fromisoformat(
                            received_at.replace("Z", "+00:00")
                        )
                        if received_at
                        else None,
                        is_unread=not bool(item.get("isRead", False)),
                        snippet=item.get("bodyPreview"),
                        thread_id=item.get("conversationId"),
                        raw=item,
                    )
                )
            messages = [
                {
                    "id": m.provider_message_id,
                    "subject": m.subject,
                    "sender": m.from_email,
                    "is_unread": m.is_unread,
                    "snippet": m.snippet,
                    "received_at": str(m.received_at) if m.received_at else None,
                    "parent_folder_id": (m.raw or {}).get("parentFolderId"),
                    "has_attachments": bool(
                        (m.raw or {}).get("hasAttachments", False)
                    ),
                    "thread_id": m.thread_id,
                    "mailbox": scoped_mailbox,
                }
                for m in provider_messages
            ]

        self.context["email_list"] = messages
        if messages:
            self.context["current_email_index"] = 1
            self.context["current_email_id"] = messages[0]["id"]

        lines = []
        for i, message in enumerate(messages, 1):
            unread_mark = " [NEU]" if message.get("is_unread") else ""
            lines.append(
                f"{i}. Von: {message.get('sender')} — {message.get('subject')}{unread_mark}"
            )
        if folder:
            prefix = f"Ordner {folder}:\n"
            return prefix + ("\n".join(lines) if lines else "Keine Emails gefunden.")
        return "\n".join(lines) if lines else "Keine Emails gefunden."

    async def _tool_triage_batch(self, args: dict) -> str:
        limit = min(max(int(args.get("limit", 10) or 10), 1), 10)
        unread_only = bool(args.get("unread_only", False))
        listing = await self._tool_list_emails(
            {
                "limit": limit,
                "unread_only": unread_only,
            }
        )
        if "Keine Emails gefunden." in listing:
            return listing
        return (
            f"Triage-Batch mit maximal {limit} Mails geladen:\n{listing}\n\n"
            "Bearbeite diese Mails zuerst. Danach kann ich die naechsten 10 laden."
        )

    async def _load_status_folder_messages(
        self,
        *,
        status: str,
        mailbox: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        scoped_connection_id, token, scoped_mailbox = await self._get_scoped_connection(
            mailbox=mailbox
        )
        policy = await AssistantService(self.db).get_mailbox_policy_by_connection(
            self.tenant_id,
            self.user_id,
            scoped_connection_id,
        )
        folder = (policy.get("status_folders") or {}).get(status) or {}
        folder_id = folder.get("folder_id")
        if not folder_id:
            raise ValidationError(f"Mailbox-Policy fuer Status '{status}' ist nicht eingerichtet")

        client = (
            self._get_graph_client()
            if token == self.access_token
            else self._get_graph_client(token)
        )
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders/{folder_id}/messages",
            params={
                "$top": str(limit),
                "$orderby": "receivedDateTime desc",
                "$select": ",".join(
                    [
                        "id",
                        "conversationId",
                        "subject",
                        "from",
                        "receivedDateTime",
                        "bodyPreview",
                    ]
                ),
            },
        )
        messages = []
        for item in data.get("value", []):
            sender = (item.get("from") or {}).get("emailAddress") or {}
            messages.append(
                {
                    "id": item.get("id"),
                    "thread_id": item.get("conversationId"),
                    "subject": item.get("subject") or "(kein Betreff)",
                    "sender": sender.get("address"),
                    "received_at": item.get("receivedDateTime"),
                    "snippet": item.get("bodyPreview") or "",
                    "mailbox": scoped_mailbox,
                }
            )
        return messages

    async def _review_status_messages(
        self,
        *,
        status: str,
        args: dict,
        default_days: int,
        context_key: str,
        empty_text: str,
        title_text: str,
    ) -> str:
        mailbox = args.get("mailbox")
        limit = min(max(int(args.get("limit", 10) or 10), 1), 10)
        older_than_days = max(int(args.get("older_than_days", default_days) or default_days), 1)
        messages = await self._load_status_folder_messages(
            status=status,
            mailbox=mailbox,
            limit=limit,
        )
        cutoff = datetime.now(UTC).timestamp() - (older_than_days * 86400)
        stale = []
        for message in messages:
            received_at = message.get("received_at")
            try:
                received_ts = datetime.fromisoformat(
                    (received_at or "").replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                received_ts = cutoff
            if received_ts <= cutoff:
                stale.append(message)
        self.context[context_key] = stale
        if not stale:
            return empty_text
        lines = []
        for index, message in enumerate(stale, start=1):
            lines.append(
                f"{index}. {message.get('sender') or '?'} — {message.get('subject')}"
                f" ({message.get('received_at') or 'unbekannt'})"
            )
        return f"{title_text}\n" + "\n".join(lines)

    async def _tool_review_waiting(self, args: dict) -> str:
        return await self._review_status_messages(
            status="WARTEN",
            args=args,
            default_days=5,
            context_key="waiting_review",
            empty_text="Keine ueberfaelligen WARTEN-Mails gefunden.",
            title_text="Review fuer WARTEN-Mails:",
        )

    async def _tool_review_stale_todos(self, args: dict) -> str:
        return await self._review_status_messages(
            status="TODO",
            args=args,
            default_days=7,
            context_key="todo_review",
            empty_text="Keine alten TODO-Mails gefunden.",
            title_text="Review fuer alte TODO-Mails:",
        )

    async def _tool_summarize_inbox(self, args: dict) -> str:
        limit = min(max(int(args.get("limit", 5)), 1), 10)
        unread_only = bool(args.get("unread_only", False))
        refresh = bool(args.get("refresh", False))

        email_list = self.context.get("email_list") or []
        if refresh or not email_list:
            await self._tool_list_emails({"limit": limit, "unread_only": unread_only})
            email_list = self.context.get("email_list") or []

        if unread_only:
            email_list = [email for email in email_list if email.get("is_unread")]
        email_list = email_list[:limit]
        if not email_list:
            return "Keine passenden Emails fuer einen Ueberblick gefunden."

        summaries = []
        important = []
        for idx, email in enumerate(email_list, 1):
            summary = await self._summarize_email_for_voice(email)
            sender = email.get("sender") or "Unbekannt"
            subject = email.get("subject") or "(kein Betreff)"
            mailbox = email.get("mailbox")
            mailbox_text = f" ({mailbox})" if mailbox else ""
            unread_mark = " [NEU]" if email.get("is_unread") else ""
            summaries.append(
                f"{idx}. {sender}{mailbox_text} — {subject}{unread_mark}: {summary}"
            )
            if email.get("is_unread") or email.get("has_attachments") or email.get(
                "is_flagged"
            ):
                important.append(f"{idx}: {subject}")

        intro = f"Ueberblick ueber {len(email_list)} Emails:"
        if important:
            intro += " Besonders relevant: " + ", ".join(important[:3]) + "."
        return intro + "\n" + "\n".join(summaries)

    async def _tool_list_mailboxes(self, _args: dict) -> str:
        connections = await self._list_voice_connections(all_mailboxes=True)
        if not connections:
            return "Keine verbundenen Postfaecher gefunden."

        lines = []
        for idx, (conn, _token, mailbox) in enumerate(connections, 1):
            label = conn.account_label or mailbox or "Unbekannt"
            lines.append(f"{idx}. {label} ({conn.provider})")
        return "\n".join(lines)

    async def _tool_count_emails(self, args: dict) -> str:
        unread_only = bool(args.get("unread_only", False))
        mailbox = args.get("mailbox")
        all_mailboxes = bool(args.get("all_mailboxes", False))
        folder = self._resolve_folder_scope(args.get("folder"))
        since = self._normalize_since_filter(args.get("since"))
        if args.get("since_last_meeting_with"):
            since = (
                await self._find_last_meeting_timestamp(
                    args["since_last_meeting_with"],
                    mailbox=mailbox,
                    all_mailboxes=all_mailboxes,
                )
                or since
            )

        connections = await self._list_voice_connections(
            mailbox=mailbox,
            all_mailboxes=all_mailboxes,
        )
        if not connections:
            return "Kein passendes Postfach gefunden."

        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if since:
            filters.append(f"receivedDateTime ge {since}")

        params = {"$top": "1", "$count": "true"}
        if filters:
            params["$filter"] = " and ".join(filters)

        total = 0
        lines = []
        for conn, token, mailbox_name in connections:
            from app.integrations.microsoft_graph.client import MicrosoftGraphClient

            client = MicrosoftGraphClient(token)
            principal = f"users/{mailbox_name}" if mailbox_name else "me"
            if folder:
                folder_id = await self._resolve_folder_id_for_mailbox(
                    token, mailbox_name, folder
                )
                if not folder_id:
                    continue
                data = await client.get(
                    f"{principal}/mailFolders/{folder_id}/messages",
                    params=params,
                    headers={"ConsistencyLevel": "eventual"},
                )
            else:
                data = await client.get(
                    f"{principal}/messages",
                    params=params,
                    headers={"ConsistencyLevel": "eventual"},
                )
            count = int(data.get("@odata.count", 0) or 0)
            total += count
            label = conn.account_label or mailbox_name or "Unbekannt"
            if all_mailboxes or mailbox:
                lines.append(f"- {label}: {count}")

        scope_label = (
            "allen Postfaechern"
            if all_mailboxes
            else (mailbox or "dem aktuellen Postfach")
        )
        if folder:
            scope_label += f" im Ordner {folder}"
        mode_label = "ungelesene " if unread_only else ""
        if lines:
            return (
                f"Es gibt {total} {mode_label}Emails in {scope_label}.\n"
                + "\n".join(lines)
            )
        return f"Es gibt {total} {mode_label}Emails in {scope_label}."

    async def _tool_list_events(self, args: dict) -> str:
        mailbox = args.get("mailbox")
        limit = min(max(int(args.get("limit", 5)), 1), 20)
        connections = await self._list_voice_connections(
            mailbox=mailbox,
            all_mailboxes=bool(not mailbox),
        )
        if not connections:
            return "Kein passendes Kalenderkonto gefunden."

        lines = []
        context_events = []
        for conn, token, mailbox_name in connections:
            events = await self._fetch_calendar_events(token, mailbox_name, limit=limit)
            for event in events[:limit]:
                when = event.starts_at.isoformat() if event.starts_at else "unbekannt"
                label = conn.account_label or mailbox_name or "Unbekannt"
                lines.append(f"- {event.title or '(ohne Titel)'} @ {when} ({label})")
                context_events.append(
                    {
                        "id": event.provider_event_id,
                        "title": event.title,
                        "starts_at": when,
                        "ends_at": event.ends_at.isoformat() if event.ends_at else None,
                        "organizer": event.organizer_email,
                        "location": event.location,
                        "attendees": [
                            attendee.get("emailAddress", {}).get("address")
                            for attendee in (event.raw or {}).get("attendees", [])
                            if attendee.get("emailAddress", {}).get("address")
                        ],
                        "mailbox": mailbox_name,
                    }
                )
            if mailbox:
                break
        self.context["calendar_events"] = context_events
        if context_events:
            self.context["current_event_index"] = 1
            self.context["current_event_id"] = context_events[0]["id"]
        return "\n".join(lines) if lines else "Keine Termine gefunden."

    async def _tool_summarize_schedule(self, args: dict) -> str:
        mailbox = args.get("mailbox")
        limit = min(max(int(args.get("limit", 5)), 1), 10)
        refresh = bool(args.get("refresh", False))

        events = self.context.get("calendar_events") or []
        if refresh or not events:
            await self._tool_list_events({"mailbox": mailbox, "limit": limit})
            events = self.context.get("calendar_events") or []

        events = events[:limit]
        if not events:
            return "Keine Termine fuer einen Ueberblick gefunden."

        lines = [f"Kalender-Ueberblick ueber {len(events)} Termine:"]
        for idx, event in enumerate(events, 1):
            title = event.get("title") or "(ohne Titel)"
            start = event.get("starts_at") or "unbekannt"
            location = event.get("location") or "kein Ort"
            organizer = event.get("organizer") or "unbekannt"
            mailbox_name = event.get("mailbox")
            mailbox_text = f" ({mailbox_name})" if mailbox_name else ""
            lines.append(
                f"{idx}. {title}{mailbox_text} um {start}, Ort: {location}, organisiert von {organizer}"
            )
        return "\n".join(lines)

    async def _tool_read_event(self, args: dict) -> str:
        event_index = args.get(
            "event_index", self.context.get("current_event_index", 1)
        )
        event = self._get_event(event_index)
        if not event:
            return "Kein Termin an dieser Position. Rufe zuerst list_events auf."

        self.context["current_event_index"] = event_index
        self.context["current_event_id"] = event.get("id")
        title = event.get("title") or "(ohne Titel)"
        starts_at = event.get("starts_at") or "unbekannt"
        ends_at = event.get("ends_at")
        organizer = event.get("organizer") or "unbekannt"
        location = event.get("location") or "kein Ort"
        attendees = event.get("attendees") or []
        attendee_text = (
            ", ".join(attendees[:5]) if attendees else "keine Teilnehmer eingetragen"
        )
        if len(attendees) > 5:
            attendee_text += f" und {len(attendees) - 5} weitere"

        time_text = f"Start: {starts_at}"
        if ends_at:
            time_text += f", Ende: {ends_at}"

        return (
            f"Termin {event_index}: {title}. {time_text}. "
            f"Organisiert von {organizer}. Ort: {location}. "
            f"Teilnehmer: {attendee_text}."
        )

    async def _tool_next_event(self, _args: dict) -> str:
        events = self.context.get("calendar_events", [])
        current = self.context.get("current_event_index", 0)
        if not events:
            return "Keine Terminliste vorhanden. Rufe zuerst list_events oder summarize_schedule auf."
        if current >= len(events):
            return "Du bist bereits beim letzten Termin."
        return await self._tool_read_event({"event_index": current + 1})

    async def _tool_previous_event(self, _args: dict) -> str:
        events = self.context.get("calendar_events", [])
        current = self.context.get("current_event_index", 1)
        if not events:
            return "Keine Terminliste vorhanden. Rufe zuerst list_events oder summarize_schedule auf."
        if current <= 1:
            return "Du bist bereits beim ersten Termin."
        return await self._tool_read_event({"event_index": current - 1})

    async def _tool_undo_last_action(self, _args: dict) -> str:
        from app.assistant.service import AssistantService

        service = AssistantService(self.db)
        undo_logs = await service.list_undo_logs(
            self.tenant_id,
            self.user_id,
            limit=20,
            undoable_only=True,
        )
        if not undo_logs:
            return "Es gibt keine rueckgaengig machbare Aktion."

        selected = None
        if self.conversation_id:
            for undo_log in undo_logs:
                if undo_log.conversation_id == self.conversation_id:
                    selected = undo_log
                    break
        selected = selected or undo_logs[0]
        result = await service.undo_action(self.tenant_id, self.user_id, selected.id)
        target = (
            (result.target_ref_json or {}).get("subject")
            or (result.target_ref_json or {}).get("email_id")
            or (result.target_ref_json or {}).get("draft_id")
            or "den letzten Vorgang"
        )
        return f"Rueckgaengig gemacht: {result.action_type} fuer {target}."

    async def _tool_cancel_pending_action(self, _args: dict) -> str:
        pending = self.context.get("pending_confirmation") or {}
        pending_id = pending.get("id")
        action = pending.get("action")
        if not pending_id or not action:
            return "Es gibt keine offene bestaetigungspflichtige Aktion."

        from app.assistant.service import AssistantService

        await AssistantService(self.db).cancel_pending_intent(
            self.tenant_id,
            self.user_id,
            pending_id,
        )
        clear_pending_intent_context(self.context)
        return f"Aktion '{action}' wurde abgebrochen."

    async def _tool_undo_last_cleanup(self, _args: dict) -> str:
        from app.assistant.service import AssistantService

        result = await AssistantService(self.db).undo_last_cleanup_batch(
            self.tenant_id, self.user_id
        )
        return (
            f"Letzter Cleanup-Batch #{result['pending_intent_id']} soweit moeglich "
            f"rueckgaengig gemacht. {result['undone_count']} von "
            f"{result['total_batch_logs']} Aktionen wurden rueckgaengig gemacht."
        )

    async def _tool_explain_email_rules(self, args: dict) -> str:
        from types import SimpleNamespace

        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_list = self.context.get("email_list", [])
        if not email_list or index < 1 or index > len(email_list):
            return "Keine Email an dieser Position. Bitte zuerst Emails auflisten."

        email = email_list[index - 1]
        rules = await self._load_cleanup_rules()
        if not rules:
            return "Es gibt aktuell keine aktiven Regeln."

        message = SimpleNamespace(
            subject=email.get("subject"),
            from_email=email.get("sender"),
            snippet=email.get("snippet"),
            raw={"parentFolderId": email.get("parent_folder_id")},
        )
        mailbox = email.get("mailbox")
        matches = []
        for rule in rules:
            if not self._rule_matches_message(rule, message, mailbox):
                continue
            action = rule.action_type
            target = (rule.action_payload_json or {}).get("target")
            action_text = action if not target else f"{action} -> {target}"
            matches.append(
                f"- {rule.name}: {action_text} (Risk: {rule.risk_level})"
            )

        if not matches:
            return "Auf diese Email passt aktuell keine aktive Regel."

        subject = email.get("subject") or "(kein Betreff)"
        return (
            f"Fuer Email '{subject}' passen {len(matches)} aktive Regeln:\n"
            + "\n".join(matches)
        )

    async def _tool_set_active_mailbox(self, args: dict) -> str:
        mailbox = (args.get("mailbox") or "").strip().lower()
        if not mailbox:
            return "Bitte gib ein Postfach an."

        connections = await self._list_voice_connections(mailbox=mailbox)
        if not connections:
            return f"Kein verbundenes Postfach '{mailbox}' gefunden."

        self.context["active_mailbox"] = mailbox
        self.context.pop("current_email_index", None)
        self.context.pop("current_email_id", None)
        return f"Postfach '{mailbox}' ist jetzt aktiv."

    async def _tool_clear_active_mailbox(self, _args: dict) -> str:
        if not self.context.get("active_mailbox"):
            return "Es ist aktuell kein Standard-Postfach gesetzt."
        mailbox = self.context.pop("active_mailbox", None)
        return f"Mailbox-Scope fuer '{mailbox}' wurde aufgehoben. Ich arbeite wieder ohne festes Postfach."

    async def _tool_set_active_folder(self, args: dict) -> str:
        folder = (args.get("folder") or "").strip()
        if not folder:
            return "Bitte gib einen Ordner an."

        folder_id = await self._resolve_folder_id(folder)
        if not folder_id:
            return f"Ordner '{folder}' wurde nicht gefunden."

        self.context["active_folder_name"] = folder
        self.context["active_folder_id"] = folder_id
        self.context.pop("current_email_index", None)
        self.context.pop("current_email_id", None)
        return f"Ordner '{folder}' ist jetzt aktiv."

    async def _tool_clear_active_folder(self, _args: dict) -> str:
        folder = self.context.pop("active_folder_name", None)
        self.context.pop("active_folder_id", None)
        if not folder:
            return "Es ist aktuell kein Standard-Ordner gesetzt."
        return f"Ordner-Scope fuer '{folder}' wurde aufgehoben."

    async def _tool_list_rule_suggestions(self, _args: dict) -> str:
        from app.assistant.learning import AssistantLearningService

        service = AssistantLearningService(self.db)
        suggestions = await service.suggest_rules(self.tenant_id, self.user_id)
        if not suggestions:
            self.context["rule_suggestions"] = []
            return "Aktuell gibt es keine neuen Regelvorschlaege."

        self.context["rule_suggestions"] = suggestions
        lines = []
        for idx, suggestion in enumerate(suggestions[:10], 1):
            lines.append(
                f"{idx}. {suggestion.get('name', 'Regelvorschlag')} — "
                f"{suggestion.get('reason', 'kein Grund angegeben')}"
            )
        return "\n".join(lines)

    async def _tool_apply_rule_suggestion(self, args: dict) -> str:
        from app.assistant.learning import AssistantLearningService

        suggestion_index = int(args.get("suggestion_index", 0))
        suggestions = self.context.get("rule_suggestions") or []
        if suggestion_index < 1 or suggestion_index > len(suggestions):
            return "Kein Regelvorschlag an dieser Position. Rufe zuerst list_rule_suggestions auf."

        suggestion = suggestions[suggestion_index - 1]
        rule = await AssistantLearningService(self.db).apply_suggestion(
            self.tenant_id,
            self.user_id,
            suggestion,
        )
        return f"Regel '{rule.name}' wurde uebernommen."

    async def _tool_accept_event(self, args: dict) -> str:
        return await self._handle_event_response(args, mode="accept")

    async def _tool_decline_event(self, args: dict) -> str:
        return await self._handle_event_response(args, mode="decline")

    async def _tool_tentative_event(self, args: dict) -> str:
        return await self._handle_event_response(args, mode="tentative")

    async def _tool_preview_cleanup(self, args: dict) -> str:
        preview = await self._build_cleanup_preview(
            mailbox=args.get("mailbox"),
            all_mailboxes=bool(args.get("all_mailboxes", False)),
            unread_only=bool(args.get("unread_only", True)),
            limit_per_mailbox=min(max(int(args.get("limit_per_mailbox", 30)), 1), 100),
        )
        self.context["cleanup_preview"] = preview
        return preview["summary"]

    async def _tool_search_emails(self, args: dict) -> str:
        query = (args.get("query") or "").strip().lower()
        if not query:
            return "Bitte gib einen Suchbegriff an."

        limit = min(max(int(args.get("limit", 10)), 1), 20)
        sender_filter = (args.get("sender") or "").strip().lower()
        folder = self._resolve_folder_scope(args.get("folder"))
        since = self._normalize_since_filter(args.get("since"))
        if args.get("since_last_meeting_with"):
            since = (
                await self._find_last_meeting_timestamp(
                    args["since_last_meeting_with"],
                    mailbox=args.get("mailbox"),
                    all_mailboxes=bool(args.get("all_mailboxes", False)),
                )
                or since
            )
        connections = await self._list_voice_connections(
            mailbox=args.get("mailbox"),
            all_mailboxes=bool(args.get("all_mailboxes", False)),
        )
        if not connections:
            return "Kein passendes Postfach gefunden."

        matches = []
        for _conn, token, mailbox_name in connections:
            if folder:
                messages = await self._fetch_folder_messages(
                    token,
                    mailbox_name,
                    folder_name=folder,
                    unread_only=bool(args.get("unread_only", False)),
                    limit=50,
                )
            else:
                messages = await self._fetch_mailbox_messages(
                    token,
                    mailbox_name,
                    unread_only=bool(args.get("unread_only", False)),
                    limit=50,
                )
            for message in messages:
                if (
                    since
                    and message.received_at
                    and message.received_at.isoformat() < since
                ):
                    continue
                sender = (message.from_email or "").lower()
                if sender_filter and sender_filter not in sender:
                    continue
                haystack = f"{message.subject or ''} {message.snippet or ''}".lower()
                if query not in haystack:
                    continue
                matches.append(
                    {
                        "id": message.provider_message_id,
                        "subject": message.subject,
                        "sender": message.from_email,
                        "snippet": message.snippet,
                        "received_at": str(message.received_at)
                        if message.received_at
                        else None,
                        "mailbox": mailbox_name,
                        "is_unread": message.is_unread,
                        "parent_folder_id": (message.raw or {}).get("parentFolderId"),
                        "has_attachments": bool(
                            (message.raw or {}).get("hasAttachments", False)
                        ),
                        "thread_id": getattr(message, "thread_id", None),
                        "folder": folder,
                    }
                )
                if len(matches) >= limit:
                    break
            if len(matches) >= limit:
                break

        self.context["email_list"] = matches
        if matches:
            self.context["current_email_index"] = 1
            self.context["current_email_id"] = matches[0]["id"]

        if not matches:
            return f"Keine Emails zu '{query}' gefunden."
        lines = []
        for idx, message in enumerate(matches, 1):
            unread_mark = " [NEU]" if message.get("is_unread") else ""
            mailbox_label = (
                f" ({message.get('mailbox')})" if message.get("mailbox") else ""
            )
            folder_label = (
                f" [{message.get('folder')}]" if message.get("folder") else ""
            )
            lines.append(
                f"{idx}. Von: {message.get('sender') or 'Unbekannt'} — "
                f"{message.get('subject') or '(kein Betreff)'}"
                f"{unread_mark}{mailbox_label}{folder_label}"
            )
        return "\n".join(lines)

    async def _tool_analyze_mailbox(self, args: dict) -> str:
        mailbox = args.get("mailbox")
        all_mailboxes = bool(args.get("all_mailboxes", False))
        unread_only = bool(args.get("unread_only", True))

        count_text = await self._tool_count_emails(
            {
                "mailbox": mailbox,
                "all_mailboxes": all_mailboxes,
                "unread_only": unread_only,
            }
        )
        preview = await self._build_cleanup_preview(
            mailbox=mailbox,
            all_mailboxes=all_mailboxes,
            unread_only=unread_only,
            limit_per_mailbox=30,
        )
        operations = preview.get("operations") or []
        recommendation = (
            "Bereinigung empfohlen."
            if operations
            else "Aktuell keine Bereinigung noetig."
        )
        return f"{count_text}\n{preview['summary']}\n{recommendation}"

    async def _tool_execute_cleanup(self, args: dict) -> str:
        preview = self.context.get("cleanup_preview") or {}
        operations = preview.get("operations") or []
        if not operations:
            return "Es gibt keine vorbereitete Cleanup-Vorschau. Rufe zuerst preview_cleanup auf."

        confirmed = bool(args.get("confirmed", False))
        if not confirmed and not self.skip_confirmation:
            intent = await self._create_pending_intent(
                "bulk_cleanup",
                target_type="cleanup_batch",
                target_ref={"operation_count": len(operations)},
                payload={"operations": operations},
            )
            return (
                f"BESTAETIGUNG ERFORDERLICH: {len(operations)} berechnete Cleanup-Aktionen ausfuehren? "
                f"Wenn der User zustimmt, rufe execute_cleanup(confirmed=true) auf. "
                f"(Batch #{intent.id})"
            )

        gate_err = await self._verify_pending_confirmation("bulk_cleanup")
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent("bulk_cleanup")
        if not pending:
            return "Keine ausstehende Bestaetigung fuer 'bulk_cleanup'."

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).execute_pending_intent(
                self.tenant_id, self.user_id, pending.id
            )
        except AppError as e:
            return e.message
        clear_pending_intent_context(self.context)
        self.context.pop("cleanup_preview", None)
        return f"Cleanup ausgefuehrt. {len(operations)} Aktionen wurden verarbeitet."

    async def _handle_event_response(self, args: dict, *, mode: str) -> str:
        event_index = args.get("event_index", 1)
        confirmed = bool(args.get("confirmed", False))
        comment = args.get("comment", "")
        event = self._get_event(event_index)
        if not event:
            return "Kein Termin an dieser Position. Rufe zuerst list_events auf."

        action_map = {
            "accept": ("accept_event", "annehmen", "angenommen"),
            "decline": ("decline_event", "ablehnen", "abgelehnt"),
            "tentative": (
                "tentative_event",
                "vorlaeufig zusagen",
                "vorlaeufig zugesagt",
            ),
        }
        intent_type, verb, result_text = action_map.get(
            mode,
            ("accept_event", "annehmen", "angenommen"),
        )
        if not confirmed and not self.skip_confirmation:
            await self._create_pending_intent(
                intent_type,
                target_type="calendar_event",
                target_ref={
                    "event_index": event_index,
                    "event_id": event.get("id"),
                    "title": event.get("title"),
                    "mailbox": event.get("mailbox"),
                },
                payload={"comment": comment},
            )
            return (
                f"BESTAETIGUNG ERFORDERLICH: Termin '{event.get('title', '(ohne Titel)')}' "
                f"wirklich {verb}? Frage den User."
            )

        gate_err = await self._verify_pending_confirmation(intent_type)
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent(intent_type)
        if not pending:
            return f"Keine ausstehende Bestaetigung fuer '{intent_type}'."

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).execute_pending_intent(
                self.tenant_id, self.user_id, pending.id
            )
        except AppError as e:
            return e.message
        clear_pending_intent_context(self.context)
        return f"Termin '{event.get('title', '(ohne Titel)')}' {result_text}."

    async def _tool_read_email(self, args: dict) -> str:
        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_list = self.context.get("email_list", [])
        if not email_list or index < 1 or index > len(email_list):
            return "Keine Email an dieser Position. Bitte zuerst Emails auflisten."

        email = email_list[index - 1]
        self.context["current_email_index"] = index
        self.context["current_email_id"] = email["id"]

        total = len(email_list)
        summary = await self._summarize_email_for_voice(email)
        unread = " [NEU]" if email.get("is_unread") else ""
        attachments = " [ANHANG]" if email.get("has_attachments") else ""
        flagged = " [MARKIERT]" if email.get("is_flagged") else ""
        return (
            f"Email {index} von {total}{unread}{attachments}{flagged}:\n"
            f"Von: {email.get('sender', 'Unbekannt')}\n"
            f"Betreff: {email.get('subject', 'Kein Betreff')}\n"
            f"Empfangen: {email.get('received_at', 'Unbekannt')}\n"
            f"Kurzfassung: {summary}"
        )

    async def _tool_read_thread(self, args: dict) -> str:
        err = self._check_provider()
        if err:
            return err

        index = args.get("email_index", self.context.get("current_email_index", 1))
        thread_id = self._get_email_thread_id(index)
        if not thread_id:
            return "Kein Thread fuer diese Email verfuegbar."

        _cid, token, scoped_mailbox = await self._get_scoped_connection(index=index)
        client = (
            self._get_graph_client()
            if token == self.access_token
            else self._get_graph_client(token)
        )
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        limit = min(max(int(args.get("limit", 10)), 1), 20)
        data = await client.get(
            f"{principal}/messages",
            params={
                "$top": str(limit),
                "$orderby": "receivedDateTime asc",
                "$filter": f"conversationId eq '{thread_id}'",
                "$select": "id,conversationId,subject,from,receivedDateTime,bodyPreview,hasAttachments,parentFolderId",
            },
        )
        items = data.get("value", [])
        if not items:
            return "Keine weiteren Nachrichten in diesem Thread gefunden."

        context_thread = []
        for idx, item in enumerate(items, 1):
            sender = (
                (item.get("from") or {})
                .get("emailAddress", {})
                .get("address", "Unbekannt")
            )
            preview = (item.get("bodyPreview") or "").strip()
            preview = preview[:160]
            context_thread.append(
                {
                    "index": idx,
                    "id": item.get("id"),
                    "subject": item.get("subject") or "(kein Betreff)",
                    "sender": sender,
                    "preview": preview,
                    "mailbox": scoped_mailbox,
                }
            )
        self.context["current_thread"] = context_thread
        self.context["current_thread_id"] = thread_id
        summary = await self._summarize_thread_for_voice(context_thread)
        lines = [f"Thread mit {len(items)} Nachrichten.", f"Zusammenfassung: {summary}"]
        for item in context_thread:
            lines.append(
                f"{item['index']}. {item['sender']} — {item['subject']}: {item['preview']}"
            )
        return "\n".join(lines)

    async def _tool_list_attachments(self, args: dict) -> str:
        err = self._check_provider()
        if err:
            return err

        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        _cid, token, scoped_mailbox = await self._get_scoped_connection(index=index)
        client = (
            self._get_graph_client()
            if token == self.access_token
            else self._get_graph_client(token)
        )
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/messages/{email_id}/attachments",
            params={"$select": "name,size,contentType"},
        )
        attachments = data.get("value", [])
        if not attachments:
            return "Diese Email hat keine Anhaenge."

        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            email_list[index - 1]["has_attachments"] = True
            email_list[index - 1]["attachments"] = attachments

        lines = []
        for attachment in attachments[:10]:
            size_kb = round((attachment.get("size") or 0) / 1024, 1)
            lines.append(
                f"- {attachment.get('name', 'Unbekannt')} "
                f"({attachment.get('contentType', 'unbekannt')}, {size_kb} KB)"
            )
        return "Anhaenge:\n" + "\n".join(lines)

    async def _tool_read_email_full(self, args: dict) -> str:
        err = self._check_provider()
        if err:
            return err

        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        self.context["current_email_index"] = index
        self.context["current_email_id"] = email_id

        _cid, token, scoped_mailbox = await self._get_scoped_connection(index=index)
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/messages/{email_id}",
            params={"$select": "subject,from,body,receivedDateTime"},
        )

        body = data.get("body", {})
        content = body.get("content", "")
        import re

        text = re.sub(r"<[^>]+>", " ", content)
        text = re.sub(r"\s+", " ", text).strip()

        return (
            f"Komplette Email:\n"
            f"Betreff: {data.get('subject', '')}\n"
            f"Von: {(data.get('from', {}).get('emailAddress', {}).get('address', 'Unbekannt'))}\n"
            f"Inhalt:\n{text[:3000]}"
        )

    # ── Destructive actions with server-side confirmation gate ───────
    #
    # The confirmation gate works in two phases:
    # Phase 1: Tool called without confirmed=true → stores pending_confirmation
    # Phase 2: Tool called with confirmed=true → backend VERIFIES that a
    #          matching pending_confirmation exists in context. If not, the
    #          action is rejected. This prevents the LLM from bypassing the
    #          confirmation by sending confirmed=true without a prior request.

    async def _verify_pending_confirmation(self, action: str) -> str | None:
        """Verify a matching pending_confirmation exists. Returns error or None.

        When skip_confirmation is active, the gate is bypassed.
        """
        if self.skip_confirmation:
            return None
        pending = await self._get_pending_intent(action)
        if not pending:
            return (
                f"Keine ausstehende Bestaetigung fuer '{action}'. "
                f"Die Aktion muss zuerst ohne confirmed=true aufgerufen werden."
            )
        return None

    async def _tool_delete_email(self, args: dict) -> str:
        index = self._resolve_email_index_for_action(args)
        confirmed = args.get("confirmed", False)
        subject = self._get_email_subject(index)
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        _conn_id = (await self._get_scoped_connection(index=index))[0]
        _target_ref = {
            "email_index": index,
            "email_id": email_id,
            "subject": subject,
            "sender": self.context.get("email_list", [{}])[index - 1].get(
                "sender", ""
            ),
            "mailbox": self._get_email_mailbox(index),
            "original_folder_id": self._get_email_folder_id(index),
        }

        if not confirmed and not self.skip_confirmation:
            await self._create_pending_intent(
                "delete_email",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
            )
            return (
                f"BESTAETIGUNG ERFORDERLICH: Email '{subject}' (Nr. {index}) loeschen? "
                f"Frage den User ob er sicher ist."
            )

        # skip_confirmation: create + execute intent in one step
        if self.skip_confirmation:
            await self._create_pending_intent(
                "delete_email",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
            )

        # Server-side verification: pending_confirmation must exist
        gate_err = await self._verify_pending_confirmation("delete_email")
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent("delete_email")
        if not pending:
            return "Keine ausstehende Bestaetigung fuer 'delete_email'."

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).execute_pending_intent(
                self.tenant_id, self.user_id, pending.id
            )
        except AppError as e:
            return e.message

        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            email_list.pop(index - 1)
        clear_pending_intent_context(self.context)

        # Advance to next email — auto-reload if list exhausted
        action_msg = f"Email nach Geloeschte Elemente verschoben: {subject}."
        return await self._advance_after_action(action_msg, email_list, index)

    async def _tool_move_email(self, args: dict) -> str:
        index = self._resolve_email_index_for_action(args)
        folder = args.get("folder", "Archive")
        confirmed = args.get("confirmed", False)
        subject = self._get_email_subject(index)
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        _conn_id = (await self._get_scoped_connection(index=index))[0]
        _target_ref = {
            "email_index": index,
            "email_id": email_id,
            "subject": subject,
            "sender": self.context.get("email_list", [{}])[index - 1].get(
                "sender", ""
            ),
            "mailbox": self._get_email_mailbox(index),
            "original_folder_id": self._get_email_folder_id(index),
            "original_folder_name": None,
        }

        if not confirmed and not self.skip_confirmation:
            await self._create_pending_intent(
                "move_email",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
                payload={"folder": folder},
            )
            return (
                f"BESTAETIGUNG ERFORDERLICH: Email '{subject}' (Nr. {index}) "
                f"nach '{folder}' verschieben? Frage den User."
            )

        # skip_confirmation: create + execute intent in one step
        if self.skip_confirmation:
            await self._create_pending_intent(
                "move_email",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
                payload={"folder": folder},
            )

        gate_err = await self._verify_pending_confirmation("move_email")
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent("move_email")
        if not pending:
            return "Keine ausstehende Bestaetigung fuer 'move_email'."

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).execute_pending_intent(
                self.tenant_id, self.user_id, pending.id
            )
        except ValidationError as e:
            return e.message

        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            email_list.pop(index - 1)
        clear_pending_intent_context(self.context)

        action_msg = f"Email '{subject}' nach '{folder}' verschoben."
        return await self._advance_after_action(action_msg, email_list, index)

    async def _tool_move_to_status(self, args: dict) -> str:
        index = self._resolve_email_index_for_action(args)
        status = (args.get("status") or "").upper()
        confirmed = args.get("confirmed", False)
        if status not in {"TODO", "WARTEN", "TEMP", "ARCHIV"}:
            return "Ungueltiger Zielstatus. Erlaubt sind TODO, WARTEN, TEMP oder ARCHIV."

        subject = self._get_email_subject(index)
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        # TEMP requires duration — calculate actual date server-side
        expires_at = None
        if status == "TEMP":
            expires_in_days = args.get("expires_in_days")
            if not expires_in_days:
                return "TEMP erfordert eine Aufbewahrungsdauer in Tagen (z.B. expires_in_days=5)."
            expires_at = (datetime.utcnow() + timedelta(days=int(expires_in_days))).isoformat()

        status_labels = {
            "TODO": "TODO",
            "WARTEN": "WARTEN",
            "TEMP": "TEMP",
            "ARCHIV": "ARCHIV",
        }
        status_label = status_labels[status]

        _conn_id = (await self._get_scoped_connection(index=index))[0]
        _target_ref = {
            "email_index": index,
            "email_id": email_id,
            "subject": subject,
            "sender": self.context.get("email_list", [{}])[index - 1].get(
                "sender", ""
            ),
            "mailbox": self._get_email_mailbox(index),
            "original_folder_id": self._get_email_folder_id(index),
            "original_folder_name": None,
            "original_status": "INBOX",
        }
        _payload = {
            "status": status,
            "expires_at": expires_at,
            "expires_in_days": args.get("expires_in_days"),
        }

        if not confirmed and not self.skip_confirmation:
            await self._create_pending_intent(
                "move_to_status",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
                payload=_payload,
            )
            temp_hint = ""
            if status == "TEMP" and args.get("expires_in_days"):
                temp_hint = f" (Aufbewahrung: {args['expires_in_days']} Tage)"
            return (
                f"BESTAETIGUNG ERFORDERLICH: Email '{subject}' (Nr. {index}) "
                f"nach '{status_label}'{temp_hint} verschieben? Frage den User."
            )

        # skip_confirmation: create + execute intent in one step
        if self.skip_confirmation:
            await self._create_pending_intent(
                "move_to_status",
                connection_id=_conn_id,
                target_type="email",
                target_ref=_target_ref,
                payload=_payload,
            )

        gate_err = await self._verify_pending_confirmation("move_to_status")
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent("move_to_status")
        if not pending:
            return "Keine ausstehende Bestaetigung fuer 'move_to_status'."

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).execute_pending_intent(
                self.tenant_id, self.user_id, pending.id
            )
        except ValidationError as e:
            return e.message

        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            email_list.pop(index - 1)
        clear_pending_intent_context(self.context)

        action_msg = f"Email '{subject}' nach '{status_label}' verschoben."
        return await self._advance_after_action(action_msg, email_list, index)

    async def _tool_set_temp_expiry(self, args: dict) -> str:
        index = self._resolve_email_index_for_action(args)
        email_id = self._get_email_id(index)
        if not email_id:
            return "Keine Email an dieser Position."

        # Calculate actual date server-side from days
        expires_in_days = args.get("expires_in_days")
        if not expires_in_days:
            return "Bitte nenne die Aufbewahrungsdauer in Tagen."
        expires_at = (datetime.utcnow() + timedelta(days=int(expires_in_days))).isoformat()

        email = {}
        email_list = self.context.get("email_list", [])
        if 1 <= index <= len(email_list):
            email = email_list[index - 1]

        scoped_connection_id, _token, scoped_mailbox = await self._get_scoped_connection(
            index=index
        )
        try:
            await AssistantService(self.db).upsert_temp_tracking(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                connection_id=scoped_connection_id,
                message_external_id=email_id,
                thread_external_id=email.get("thread_id"),
                mailbox_address=scoped_mailbox or email.get("mailbox"),
                subject=email.get("subject"),
                sender=email.get("sender"),
                expires_at=expires_at,
                metadata_json={"source": "set_temp_expiry"},
            )
        except ValidationError as e:
            return e.message

        email["temp_expires_at"] = expires_at
        self.context["temp_review"] = None
        return (
            f"Verfallsdatum fuer Email '{self._get_email_subject(index)}' "
            f"auf {expires_at} gesetzt."
        )

    async def _tool_review_expired_temp(self, args: dict) -> str:
        mailbox = args.get("mailbox")
        limit = max(1, min(int(args.get("limit", 10) or 10), 20))
        items = await AssistantService(self.db).review_expired_temp(
            self.tenant_id,
            self.user_id,
            mailbox=mailbox,
            limit=limit,
        )
        self.context["temp_review"] = [
            {
                "message_id": item.message_external_id,
                "mailbox": item.mailbox_address,
                "subject": item.subject,
                "sender": item.sender,
                "expires_at": item.expires_at.isoformat(),
            }
            for item in items
        ]
        if not items:
            return "Es gibt aktuell keine abgelaufenen TEMP-Mails."
        lines = []
        for idx, item in enumerate(items, start=1):
            mailbox_hint = f" [{item.mailbox_address}]" if item.mailbox_address else ""
            lines.append(
                f"{idx}. {item.sender or '?'} — {item.subject or '(kein Betreff)'}"
                f"{mailbox_hint}, abgelaufen seit {item.expires_at.date().isoformat()}"
            )
        return f"{len(items)} abgelaufene TEMP-Mails:\n" + "\n".join(lines)

    async def _tool_archive_email(self, args: dict) -> str:
        """Archive an email via the status-based move flow."""
        return await self._tool_move_to_status(
            {
                "email_index": self._resolve_email_index_for_action(args),
                "status": "ARCHIV",
                "confirmed": args.get("confirmed", False),
            }
        )

    async def _tool_reply_to_email(self, args: dict) -> str:
        """Create a draft reply — does NOT send. User must confirm_and_send."""
        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_id = self._get_email_id(index)
        reply_text = args.get("reply_text", "")
        if not email_id:
            return "Keine Email an dieser Position."

        email_list = self.context.get("email_list", [])
        sender = ""
        subject = ""
        if 1 <= index <= len(email_list):
            sender = email_list[index - 1].get("sender", "")
            subject = email_list[index - 1].get("subject", "")

        draft = await self._create_draft(
            connection_id=(await self._get_scoped_connection(index=index))[0],
            draft_type="reply",
            target_external_id=email_id,
            subject=subject,
            body_text=reply_text,
            recipients=[sender] if sender else [],
            metadata={"email_index": index},
        )
        return (
            f"Entwurf #{draft.id} erstellt fuer Antwort an {sender} "
            f"(Betreff: {subject}):\n\n{reply_text}\n\n"
            f"Lies diesen Entwurf dem User vor und frage: 'Soll ich das so absenden?'"
        )

    async def _tool_forward_email(self, args: dict) -> str:
        """Forward current email to another address via Graph forward API."""
        index = self._resolve_email_index_for_action(args)
        email_id = self._get_email_id(index)
        subject = self._get_email_subject(index)
        to = args.get("to", "")
        comment = args.get("comment")
        confirmed = args.get("confirmed", False)

        if not email_id:
            return "Keine Email an dieser Position."
        if not to:
            return "Bitte nenne die Empfaenger-Adresse fuer die Weiterleitung."

        _fwd_target_ref = {
            "email_index": index,
            "email_id": email_id,
            "subject": subject,
            "to": to,
        }
        _fwd_payload = {
            "to": to,
            "comment": comment,
        }

        if not confirmed and not self.skip_confirmation:
            await self._create_pending_intent(
                "forward_email",
                target_type="email",
                target_ref=_fwd_target_ref,
                payload=_fwd_payload,
            )
            comment_hint = f" mit Kommentar: '{comment}'" if comment else " kommentarlos"
            return (
                f"BESTAETIGUNG ERFORDERLICH: Email '{subject}' an {to} weiterleiten{comment_hint}? "
                f"Frage den User."
            )

        # skip_confirmation: create + execute intent in one step
        if self.skip_confirmation:
            await self._create_pending_intent(
                "forward_email",
                target_type="email",
                target_ref=_fwd_target_ref,
                payload=_fwd_payload,
            )

        # Server-side verification
        gate_err = await self._verify_pending_confirmation("forward_email")
        if gate_err:
            return gate_err
        pending = await self._get_pending_intent("forward_email")
        if not pending:
            return "Keine ausstehende Bestaetigung fuer 'forward_email'."

        err = self._check_provider()
        if err:
            return err

        # Execute forward via Graph API
        _cid, token, scoped_mailbox = await self._get_scoped_connection(index=index)
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient
        from app.integrations.microsoft_graph.mail_actions import (
            MicrosoftGraphMailActionProvider,
        )

        client = MicrosoftGraphClient(token)
        action_provider = MicrosoftGraphMailActionProvider(client)
        fwd_to = pending.payload_json.get("to", to)
        fwd_comment = pending.payload_json.get("comment")
        await action_provider.forward_message(
            email_id, [fwd_to], comment=fwd_comment, mailbox=scoped_mailbox
        )

        # Mark intent as executed
        from app.assistant.service import AssistantService
        await AssistantService(self.db).execute_pending_intent(
            self.tenant_id, self.user_id, pending.id
        )

        from app.assistant.voice_runtime import clear_pending_intent_context
        clear_pending_intent_context(self.context)

        return f"Email '{subject}' an {fwd_to} weitergeleitet."

    async def _tool_compose_email(self, args: dict) -> str:
        """Create a new outbound draft — does NOT send. User must confirm_and_send."""
        to = (args.get("to") or "").strip()
        subject = (args.get("subject") or "").strip()
        body = (args.get("body") or "").strip()
        if not to:
            return "Bitte gib einen Empfaenger an."
        if not subject:
            return "Bitte gib einen Betreff an."
        if not body:
            return "Bitte gib einen Text an."

        draft = await self._create_draft(
            connection_id=(await self._get_scoped_connection())[0],
            draft_type="new",
            target_external_id=None,
            subject=subject,
            body_text=body,
            recipients=[to],
            metadata={"compose": True},
        )
        return (
            f"Neuer Entwurf #{draft.id} erstellt fuer {to} "
            f"(Betreff: {subject}):\n\n{body}\n\n"
            f"Lies diesen Entwurf dem User vor und frage: 'Soll ich das so absenden?'"
        )

    async def _tool_preview_draft(self, _args: dict) -> str:
        draft_row = await self._get_pending_draft()
        if not draft_row:
            return "Kein offener Entwurf vorhanden."

        recipients = ", ".join((draft_row.to_recipients_json or {}).get("items", []))
        recipients = recipients or "kein Empfaenger"
        subject = draft_row.subject or "(kein Betreff)"
        body = (draft_row.body_text or "").strip() or "(leer)"
        return (
            f"Entwurf #{draft_row.id}.\n"
            f"An: {recipients}\n"
            f"Betreff: {subject}\n"
            f"Text: {body}"
        )

    async def _tool_revise_draft(self, args: dict) -> str:
        draft_row = await self._get_pending_draft()
        if not draft_row:
            return "Kein offener Entwurf vorhanden."

        from app.assistant.service import AssistantService

        updates = {"body_text": (args.get("body") or "").strip()}
        if args.get("subject") is not None:
            updates["subject"] = (args.get("subject") or "").strip()
        updated = await AssistantService(self.db).update_draft(
            self.tenant_id,
            self.user_id,
            draft_row.id,
            updates,
        )
        recipients = (getattr(updated, "to_recipients_json", None) or {}).get(
            "items", [""]
        )
        set_pending_draft_context(
            self.context,
            updated.id,
            sender=recipients[0] if recipients else "",
            subject=getattr(updated, "subject", "") or "",
            reply_text=getattr(updated, "body_text", "") or "",
            email_id=getattr(updated, "target_external_id", None),
            draft_type=getattr(updated, "draft_type", None) or "reply",
        )
        set_pending_intent_context(
            self.context,
            None,
            "send_draft",
            target_ref={
                "draft_id": updated.id,
                "subject": getattr(updated, "subject", "") or "",
                "to": recipients[0] if recipients else "",
            },
        )
        return (
            f"Entwurf #{updated.id} aktualisiert. "
            f"Neuer Betreff: {updated.subject or '(kein Betreff)'}. "
            f"Soll ich ihn vorlesen oder absenden?"
        )

    async def _tool_discard_draft(self, _args: dict) -> str:
        draft_row = await self._get_pending_draft()
        if not draft_row:
            return "Kein offener Entwurf vorhanden."

        from app.assistant.service import AssistantService

        await AssistantService(self.db).discard_draft(
            self.tenant_id, self.user_id, draft_row.id
        )
        clear_pending_draft_context(self.context)
        pending = self.context.get("pending_confirmation") or {}
        if pending.get("action") == "send_draft":
            clear_pending_intent_context(self.context)
        return f"Entwurf #{draft_row.id} wurde verworfen."

    async def _tool_confirm_and_send(self, args: dict) -> str:
        """Send the pending draft after explicit server-verified confirmation."""
        draft_row = await self._get_pending_draft()
        if not draft_row:
            return "Kein Entwurf vorhanden. Erstelle zuerst einen mit reply_to_email oder compose_email."

        confirmed = bool(args.get("confirmed", False))
        if not confirmed and not self.skip_confirmation:
            recipients = (draft_row.to_recipients_json or {}).get("items", [])
            recipient = recipients[0] if recipients else ""
            subject = draft_row.subject or "(kein Betreff)"
            set_pending_intent_context(
                self.context,
                None,
                "send_draft",
                target_ref={
                    "draft_id": draft_row.id,
                    "subject": subject,
                    "to": recipient,
                },
            )
            return (
                f"BESTAETIGUNG ERFORDERLICH: Entwurf an {recipient} senden?\n"
                f"Betreff: {subject}\n"
                f"Frage den User ob ich den Entwurf jetzt wirklich absenden soll."
            )

        gate_err = await self._verify_pending_confirmation("send_draft")
        if gate_err:
            return gate_err

        from app.assistant.service import AssistantService

        try:
            await AssistantService(self.db).send_draft(
                self.tenant_id, self.user_id, draft_row.id
            )
        except AppError as e:
            return e.message

        recipients = (draft_row.to_recipients_json or {}).get("items", [])
        sender = recipients[0] if recipients else ""
        clear_pending_draft_context(self.context)
        clear_pending_intent_context(self.context)
        return f"Entwurf gesendet an {sender}."

    async def _tool_mark_read(self, args: dict) -> str:
        return await self._set_read_state(args, True)

    async def _tool_mark_unread(self, args: dict) -> str:
        return await self._set_read_state(args, False)

    async def _tool_flag_email(self, args: dict) -> str:
        return await self._set_flag_state(args, True)

    async def _tool_unflag_email(self, args: dict) -> str:
        return await self._set_flag_state(args, False)

    async def _tool_send_email(self, args: dict) -> str:
        # Backward-compatible alias: the send flow is draft-first now.
        return await self._tool_compose_email(
            {
                "to": args.get("to", ""),
                "subject": args.get("subject", ""),
                "body": args.get("body", ""),
            }
        )

    async def _set_read_state(self, args: dict, is_read: bool) -> str:
        err = self._check_provider()
        if err:
            return err

        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_id = self._get_email_id(index)
        subject = self._get_email_subject(index)
        if not email_id:
            return "Keine Email an dieser Position."

        from app.integrations.microsoft_graph.mail_actions import (
            MicrosoftGraphMailActionProvider,
        )

        connection_id, token, scoped_mailbox = await self._get_scoped_connection(
            index=index
        )
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        action_provider = MicrosoftGraphMailActionProvider(client)
        email_list = self.context.get("email_list", [])
        previous_is_unread = None
        if 1 <= index <= len(email_list):
            previous_is_unread = email_list[index - 1].get("is_unread")
        previous_is_read = (
            None if previous_is_unread is None else not bool(previous_is_unread)
        )
        await action_provider.update_message(
            email_id,
            {"isRead": is_read},
            mailbox=scoped_mailbox,
        )

        if 1 <= index <= len(email_list):
            email_list[index - 1]["is_unread"] = not is_read

        if previous_is_read is not None:
            from app.assistant.service import AssistantService

            await AssistantService(self.db).record_mail_state_change(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                connection_id=connection_id,
                action_type="mark_read" if is_read else "mark_unread",
                email_id=email_id,
                subject=subject,
                mailbox=scoped_mailbox,
                before_state={"is_read": previous_is_read},
                after_state={"is_read": is_read},
            )

        if is_read:
            return f"Email '{subject}' als gelesen markiert."
        return f"Email '{subject}' als ungelesen markiert."

    async def _set_flag_state(self, args: dict, is_flagged: bool) -> str:
        err = self._check_provider()
        if err:
            return err

        index = args.get("email_index", self.context.get("current_email_index", 1))
        email_id = self._get_email_id(index)
        subject = self._get_email_subject(index)
        if not email_id:
            return "Keine Email an dieser Position."

        from app.integrations.microsoft_graph.mail_actions import (
            MicrosoftGraphMailActionProvider,
        )

        connection_id, token, scoped_mailbox = await self._get_scoped_connection(
            index=index
        )
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        action_provider = MicrosoftGraphMailActionProvider(client)
        email_list = self.context.get("email_list", [])
        previous_is_flagged = None
        if 1 <= index <= len(email_list):
            previous_is_flagged = email_list[index - 1].get("is_flagged")
        await action_provider.update_message(
            email_id,
            {"flag": {"flagStatus": "flagged" if is_flagged else "notFlagged"}},
            mailbox=scoped_mailbox,
        )

        if 1 <= index <= len(email_list):
            email_list[index - 1]["is_flagged"] = is_flagged

        if previous_is_flagged is not None:
            from app.assistant.service import AssistantService

            await AssistantService(self.db).record_mail_state_change(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                connection_id=connection_id,
                action_type="flag_email" if is_flagged else "unflag_email",
                email_id=email_id,
                subject=subject,
                mailbox=scoped_mailbox,
                before_state={"is_flagged": previous_is_flagged},
                after_state={"is_flagged": is_flagged},
            )

        if is_flagged:
            return f"Email '{subject}' markiert."
        return f"Markierung fuer Email '{subject}' entfernt."

    async def _tool_list_folders(self, _args: dict) -> str:
        err = self._check_provider()
        if err:
            return err

        _cid, token, scoped_mailbox = await self._get_scoped_connection()
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={
                "$select": "id,displayName,totalItemCount,unreadItemCount",
                "$top": "50",
            },
        )
        folders = data.get("value", [])
        lines = []
        for f in folders:
            name = f.get("displayName", "")
            total = f.get("totalItemCount", 0)
            unread = f.get("unreadItemCount", 0)
            lines.append(f"- {name} ({total} Emails, {unread} ungelesen)")

        self.context["folders"] = {
            f.get("displayName", "").lower(): f.get("id", "") for f in folders
        }
        return "\n".join(lines) if lines else "Keine Ordner gefunden."

    async def _advance_after_action(
        self, action_msg: str, email_list: list, removed_index: int
    ) -> str:
        """After delete/move: advance to next email or auto-reload from Inbox."""
        remaining = len(email_list)
        if remaining > 0:
            new_index = min(removed_index, remaining)
            self.context["current_email_index"] = new_index
            self.context["current_email_id"] = email_list[new_index - 1]["id"]
            next_email = email_list[new_index - 1]
            return (
                f"{action_msg} "
                f"Naechste Email ({new_index}/{remaining}): "
                f"Von {next_email.get('sender', '?')} — {next_email.get('subject', '?')}. "
                f"Was soll ich damit tun?"
            )

        # List empty — auto-reload fresh emails from Inbox
        await self._tool_list_emails({"limit": 5})
        email_list = self.context.get("email_list", [])
        if not email_list:
            return f"{action_msg} Keine weiteren Emails im Posteingang."

        next_email = email_list[0]
        return (
            f"{action_msg} "
            f"Naechste Email (1/{len(email_list)}): "
            f"Von {next_email.get('sender', '?')} — {next_email.get('subject', '?')}. "
            f"Was soll ich damit tun?"
        )

    async def _tool_next_email(self, _args: dict) -> str:
        email_list = self.context.get("email_list", [])
        current = self.context.get("current_email_index", 0)
        if not email_list or current >= len(email_list):
            # Liste leer oder am Ende — lade frische Emails nach
            await self._tool_list_emails({"limit": 5})
            email_list = self.context.get("email_list", [])
            if not email_list:
                return "Keine weiteren Emails vorhanden."
            return await self._tool_read_email({"email_index": 1})

        self.context["current_email_index"] = current + 1
        self.context["current_email_id"] = email_list[current]["id"]
        return await self._tool_read_email({"email_index": current + 1})

    async def _tool_previous_email(self, _args: dict) -> str:
        current = self.context.get("current_email_index", 1)
        if current <= 1:
            return "Du bist bereits bei der ersten Email."
        self.context["current_email_index"] = current - 1
        email_list = self.context.get("email_list", [])
        self.context["current_email_id"] = email_list[current - 2]["id"]
        return await self._tool_read_email({"email_index": current - 1})

    async def _tool_create_rule(self, args: dict) -> str:
        from app.assistant.models import AssistantRule

        # Build match_criteria using fields the rule engine actually understands
        match_criteria = {}
        if args.get("sender_contains"):
            match_criteria["sender_contains"] = args["sender_contains"]
        if args.get("subject_contains"):
            match_criteria["subject_contains"] = args["subject_contains"]

        if not match_criteria:
            return "Mindestens ein Kriterium (sender_contains oder subject_contains) ist erforderlich."

        rule = AssistantRule(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name=args.get("name", "Voice-Regel"),
            enabled=True,
            scope="user",
            priority=10,
            match_criteria_json=match_criteria,
            action_type=args.get("action", "label"),
            action_payload_json={
                "target": args.get("action_target", ""),
            },
            risk_level="low",
            origin="voice",
        )
        self.db.add(rule)
        await self.db.flush()
        criteria_desc = ", ".join(f"{k}='{v}'" for k, v in match_criteria.items())
        return f"Regel '{rule.name}' erstellt: {args.get('action', '')} fuer {criteria_desc}"

    async def _tool_read_autopilot_report(self, args: dict) -> str:
        from app.assistant.autopilot_report import AutopilotReportService

        svc = AutopilotReportService(self.db)
        return await svc.get_report_text(self.tenant_id, self.user_id)

    async def _resolve_folder_id(self, folder_name: str) -> str | None:
        """Resolve folder display name to Graph folder ID."""
        folders = self.context.get("folders")
        if folders:
            folder_id = folders.get(folder_name.lower())
            if folder_id:
                return folder_id

        _cid, token, scoped_mailbox = await self._get_scoped_connection()
        from app.integrations.microsoft_graph.client import MicrosoftGraphClient

        client = MicrosoftGraphClient(token)
        principal = f"users/{scoped_mailbox}" if scoped_mailbox else "me"
        data = await client.get(
            f"{principal}/mailFolders",
            params={"$select": "id,displayName", "$top": "50"},
        )
        folder_map = {
            f.get("displayName", "").lower(): f.get("id", "")
            for f in data.get("value", [])
        }
        self.context["folders"] = folder_map
        return folder_map.get(folder_name.lower())
