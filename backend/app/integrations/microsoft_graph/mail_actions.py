"""Mutating mailbox actions via Microsoft Graph."""

from app.integrations.interfaces import MailActionProvider, MailSendProvider
from app.integrations.microsoft_graph.client import MicrosoftGraphClient
from app.integrations.types import MailDraft


class MicrosoftGraphMailActionProvider(MailActionProvider, MailSendProvider):
    """Send and mutate Outlook messages behind shared interfaces."""

    def __init__(self, client: MicrosoftGraphClient) -> None:
        self.client = client

    async def send_mail(
        self,
        draft: MailDraft,
        *,
        mailbox: str | None = None,
    ) -> dict:
        principal = f"users/{mailbox}" if mailbox else "me"
        payload = {"message": self._build_message_payload(draft), "saveToSentItems": True}
        return await self.client.post(f"{principal}/sendMail", json=payload)

    async def reply_to_message(
        self,
        provider_message_id: str,
        draft: MailDraft,
        *,
        mailbox: str | None = None,
    ) -> dict:
        principal = f"users/{mailbox}" if mailbox else "me"
        payload = {
            "message": {
                "body": {"contentType": "HTML", "content": draft.html_body},
                "toRecipients": self._recipient_payload(draft.to_recipients),
                "ccRecipients": self._recipient_payload(draft.cc_recipients),
            }
        }
        return await self.client.post(
            f"{principal}/messages/{provider_message_id}/reply",
            json=payload,
        )

    async def delete_message(
        self,
        provider_message_id: str,
        *,
        mailbox: str | None = None,
    ) -> None:
        principal = f"users/{mailbox}" if mailbox else "me"
        await self.client.delete(f"{principal}/messages/{provider_message_id}")

    async def move_message(
        self,
        provider_message_id: str,
        destination_folder: str,
        *,
        mailbox: str | None = None,
    ) -> dict:
        principal = f"users/{mailbox}" if mailbox else "me"
        return await self.client.post(
            f"{principal}/messages/{provider_message_id}/move",
            json={"destinationId": destination_folder},
        )

    async def forward_message(
        self,
        provider_message_id: str,
        to_recipients: list[str],
        comment: str | None = None,
        *,
        mailbox: str | None = None,
    ) -> dict:
        """Forward a message with all its attachments via Graph API."""
        principal = f"users/{mailbox}" if mailbox else "me"
        payload = {
            "toRecipients": self._recipient_payload(to_recipients),
        }
        if comment:
            payload["comment"] = comment
        return await self.client.post(
            f"{principal}/messages/{provider_message_id}/forward",
            json=payload,
        )

    async def update_message(
        self,
        provider_message_id: str,
        updates: dict,
        *,
        mailbox: str | None = None,
    ) -> dict:
        principal = f"users/{mailbox}" if mailbox else "me"
        return await self.client.patch(
            f"{principal}/messages/{provider_message_id}",
            json=updates,
        )

    def _build_message_payload(self, draft: MailDraft) -> dict:
        payload = {
            "subject": draft.subject,
            "body": {"contentType": "HTML", "content": draft.html_body},
            "toRecipients": self._recipient_payload(draft.to_recipients),
        }
        if draft.cc_recipients:
            payload["ccRecipients"] = self._recipient_payload(draft.cc_recipients)
        if draft.bcc_recipients:
            payload["bccRecipients"] = self._recipient_payload(draft.bcc_recipients)
        if draft.reply_to:
            payload["replyTo"] = self._recipient_payload([draft.reply_to])
        return payload

    @staticmethod
    def _recipient_payload(emails: list[str]) -> list[dict]:
        return [{"emailAddress": {"address": email}} for email in emails]
