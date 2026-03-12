"""Base email provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.emailmarketing.models import EmailProvider as EmailProviderModel


@dataclass
class EmailMessage:
    """Email message to be sent."""

    to_email: str
    to_name: str | None
    subject: str
    html_content: str
    text_content: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    reply_to: str | None = None
    headers: dict = field(default_factory=dict)
    tracking_token: str | None = None  # For open/click tracking


@dataclass
class SendResult:
    """Result of sending an email."""

    success: bool
    message_id: str | None = None
    error: str | None = None
    provider_response: dict | None = None


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    def __init__(self, config: "EmailProviderModel") -> None:
        """Initialize with provider configuration."""
        self.config = config
        self.sender_email = config.sender_email
        self.sender_name = config.sender_name
        self.reply_to = config.reply_to_email

    @abstractmethod
    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email.

        Args:
            message: The email message to send.

        Returns:
            SendResult with success status and message ID or error.
        """
        pass

    @abstractmethod
    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 100
    ) -> list[SendResult]:
        """Send multiple emails in batches.

        Args:
            messages: List of email messages to send.
            batch_size: Number of emails per batch (provider-specific limits).

        Returns:
            List of SendResult objects, one per message.
        """
        pass

    @abstractmethod
    async def verify_credentials(self) -> bool:
        """Verify that the provider credentials are valid.

        Returns:
            True if credentials are valid, False otherwise.
        """
        pass

    def _prepare_message(self, message: EmailMessage) -> EmailMessage:
        """Prepare message with default sender info if not specified."""
        if not message.from_email:
            message.from_email = self.sender_email
        if not message.from_name:
            message.from_name = self.sender_name
        if not message.reply_to and self.reply_to:
            message.reply_to = self.reply_to
        return message


def get_provider(config: "EmailProviderModel") -> EmailProvider:
    """Factory function to get the appropriate provider implementation.

    Args:
        config: EmailProvider model with configuration.

    Returns:
        Appropriate EmailProvider implementation.

    Raises:
        ValueError: If provider type is not supported.
    """
    from app.emailmarketing.providers.mailgun import MailgunProvider
    from app.emailmarketing.providers.o365 import O365Provider
    from app.emailmarketing.providers.sendgrid import SendGridProvider

    providers = {
        "sendgrid": SendGridProvider,
        "mailgun": MailgunProvider,
        "o365": O365Provider,
    }

    provider_class = providers.get(config.provider_type)
    if not provider_class:
        raise ValueError(f"Unsupported provider type: {config.provider_type}")

    return provider_class(config)
