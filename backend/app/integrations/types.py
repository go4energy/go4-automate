"""Provider-agnostic types for external integrations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class IntegrationProvider(StrEnum):
    """Supported external provider families."""

    MICROSOFT_GRAPH = "microsoft_graph"
    GOOGLE_WORKSPACE = "google_workspace"
    IMAP = "imap"


class AuthMode(StrEnum):
    """How the platform authenticates against a provider."""

    DELEGATED = "delegated"
    APPLICATION = "application"


class ConnectionScope(StrEnum):
    """Business scope of a connection."""

    PERSONAL = "personal"
    SHARED_MAILBOX = "shared_mailbox"
    SERVICE_ACCOUNT = "service_account"


class IntegrationCapability(StrEnum):
    """Allowed operations on a connection."""

    READ_MAIL = "read_mail"
    READ_CALENDAR = "read_calendar"
    SEND_MAIL = "send_mail"
    MAIL_ACTIONS = "mail_actions"


@dataclass(slots=True)
class IntegrationConnectionDescriptor:
    """Runtime description of a provider connection."""

    tenant_id: str
    provider: IntegrationProvider
    auth_mode: AuthMode
    scope: ConnectionScope
    external_account_id: str | None = None
    user_id: int | None = None
    mailbox_address: str | None = None
    granted_capabilities: set[IntegrationCapability] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MailMessageRef:
    """Minimal provider-agnostic mail reference."""

    provider_message_id: str
    subject: str
    from_email: str | None
    received_at: datetime | None
    is_unread: bool
    snippet: str | None = None
    thread_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CalendarEventRef:
    """Minimal provider-agnostic calendar event."""

    provider_event_id: str
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    organizer_email: str | None = None
    location: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MailDraft:
    """Provider-agnostic outbound email payload."""

    subject: str
    html_body: str
    text_body: str | None
    to_recipients: list[str]
    cc_recipients: list[str] = field(default_factory=list)
    bcc_recipients: list[str] = field(default_factory=list)
    reply_to: str | None = None
    in_reply_to_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
