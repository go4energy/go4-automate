"""Email providers - SendGrid, Mailgun, Office 365."""

from app.emailmarketing.providers.base import (
    EmailMessage,
    EmailProvider,
    SendResult,
    get_provider,
)
from app.emailmarketing.providers.mailgun import MailgunProvider
from app.emailmarketing.providers.o365 import O365Provider
from app.emailmarketing.providers.sendgrid import SendGridProvider

__all__ = [
    "EmailMessage",
    "EmailProvider",
    "MailgunProvider",
    "O365Provider",
    "SendGridProvider",
    "SendResult",
    "get_provider",
]
