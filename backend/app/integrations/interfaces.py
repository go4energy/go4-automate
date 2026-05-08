"""Provider-agnostic integration interfaces."""

from typing import Protocol

from app.integrations.types import CalendarEventRef, MailDraft, MailMessageRef


class MailReadProvider(Protocol):
    """Read-only access to mailbox content."""

    async def list_messages(
        self,
        *,
        mailbox: str | None = None,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[MailMessageRef]:
        """Return normalized messages for a mailbox."""


class CalendarReadProvider(Protocol):
    """Read-only access to calendar events."""

    async def list_events(
        self,
        *,
        mailbox: str | None = None,
        limit: int = 20,
    ) -> list[CalendarEventRef]:
        """Return normalized calendar events."""


class MailSendProvider(Protocol):
    """Outbound email capabilities."""

    async def send_mail(
        self,
        draft: MailDraft,
        *,
        mailbox: str | None = None,
    ) -> dict:
        """Send a mail and return provider metadata."""


class MailActionProvider(Protocol):
    """Mutating mailbox actions."""

    async def reply_to_message(
        self,
        provider_message_id: str,
        draft: MailDraft,
        *,
        mailbox: str | None = None,
    ) -> dict:
        """Reply to an existing message."""

    async def delete_message(
        self,
        provider_message_id: str,
        *,
        mailbox: str | None = None,
    ) -> None:
        """Delete a message."""

    async def move_message(
        self,
        provider_message_id: str,
        destination_folder: str,
        *,
        mailbox: str | None = None,
    ) -> dict:
        """Move a message to another folder."""

    async def update_message(
        self,
        provider_message_id: str,
        updates: dict,
        *,
        mailbox: str | None = None,
    ) -> dict:
        """Patch message fields such as read state."""
