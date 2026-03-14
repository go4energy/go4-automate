"""Read-only mailbox access via Microsoft Graph."""

from datetime import datetime

from app.integrations.interfaces import MailReadProvider
from app.integrations.microsoft_graph.client import MicrosoftGraphClient
from app.integrations.types import MailMessageRef


class MicrosoftGraphMailReadProvider(MailReadProvider):
    """Normalize Outlook mailbox reads behind the shared interface."""

    def __init__(self, client: MicrosoftGraphClient) -> None:
        self.client = client

    async def list_messages(
        self,
        *,
        mailbox: str | None = None,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[MailMessageRef]:
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
                ]
            ),
        }
        if unread_only:
            params["$filter"] = "isRead eq false"

        principal = f"users/{mailbox}" if mailbox else "me"
        payload = await self.client.get(f"{principal}/messages", params=params)
        return [self._normalize_message(item) for item in payload.get("value", [])]

    @staticmethod
    def _normalize_message(item: dict) -> MailMessageRef:
        sender = (item.get("from") or {}).get("emailAddress") or {}
        received_at = item.get("receivedDateTime")
        return MailMessageRef(
            provider_message_id=item["id"],
            subject=item.get("subject") or "",
            from_email=sender.get("address"),
            received_at=datetime.fromisoformat(received_at.replace("Z", "+00:00"))
            if received_at
            else None,
            is_unread=not bool(item.get("isRead", False)),
            snippet=item.get("bodyPreview"),
            thread_id=item.get("conversationId"),
            raw=item,
        )
