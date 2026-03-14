"""Shared integration layer for mailbox, calendar, and provider capabilities."""

from app.integrations.interfaces import (
    CalendarReadProvider,
    MailActionProvider,
    MailReadProvider,
    MailSendProvider,
)
from app.integrations.types import (
    AuthMode,
    ConnectionScope,
    IntegrationCapability,
    IntegrationProvider,
)

__all__ = [
    "AuthMode",
    "CalendarReadProvider",
    "ConnectionScope",
    "IntegrationCapability",
    "IntegrationProvider",
    "MailActionProvider",
    "MailReadProvider",
    "MailSendProvider",
]
