"""Email providers - Brevo, SendGrid, Mailgun, Office 365, AWS SES."""

from app.emailmarketing.providers.aws_ses import AwsSesProvider
from app.emailmarketing.providers.base import (
    EmailMessage,
    EmailProvider,
    SendResult,
    get_provider,
)
from app.emailmarketing.providers.brevo import BrevoProvider
from app.emailmarketing.providers.mailgun import MailgunProvider
from app.emailmarketing.providers.o365 import O365Provider
from app.emailmarketing.providers.sendgrid import SendGridProvider

__all__ = [
    "AwsSesProvider",
    "BrevoProvider",
    "EmailMessage",
    "EmailProvider",
    "MailgunProvider",
    "O365Provider",
    "SendGridProvider",
    "SendResult",
    "get_provider",
]
