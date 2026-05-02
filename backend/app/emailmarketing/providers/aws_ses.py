"""AWS SES email provider implementation.

Uses ``SendRawEmail`` (over boto3) so we can set the RFC822 ``Message-ID``
header on outbound mails — required for the inbound reply-poller to match
replies via ``In-Reply-To`` / ``References``.

Credentials are stored as JSON inside the existing ``api_key_encrypted``
column (Fernet-encrypted at rest):

    {
      "aws_access_key_id": "AKIA...",
      "aws_secret_access_key": "...",
      "region": "eu-central-1",
      "configuration_set": "ses-smartladen"   // optional, for SNS bounces
    }

EU-Region (``eu-central-1`` Frankfurt) is the default for DSGVO-compliant
hosting of email content + delivery telemetry.
"""

from __future__ import annotations

import asyncio
import json
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr
from typing import TYPE_CHECKING

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from loguru import logger

from app.emailmarketing.encryption import decrypt_api_key
from app.emailmarketing.providers.base import (
    EmailMessage,
    EmailProvider,
    SendResult,
)

if TYPE_CHECKING:
    from app.emailmarketing.models import EmailProvider as EmailProviderModel


DEFAULT_REGION = "eu-central-1"


def _parse_credentials(api_key_encrypted: str | None) -> dict:
    """Parse the JSON credential bundle stored in api_key_encrypted."""
    if not api_key_encrypted:
        raise ValueError("AWS SES credentials missing")
    decrypted = decrypt_api_key(api_key_encrypted)
    try:
        creds = json.loads(decrypted)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid AWS SES credential JSON: {e}") from e
    if not creds.get("aws_access_key_id") or not creds.get("aws_secret_access_key"):
        raise ValueError(
            "AWS SES credentials must include aws_access_key_id and aws_secret_access_key"
        )
    return creds


class AwsSesProvider(EmailProvider):
    """AWS SES provider using boto3 + SendRawEmail."""

    def __init__(self, config: EmailProviderModel) -> None:
        super().__init__(config)
        creds = _parse_credentials(config.api_key_encrypted)
        self._access_key = creds["aws_access_key_id"]
        self._secret_key = creds["aws_secret_access_key"]
        self._region = creds.get("region") or DEFAULT_REGION
        self._configuration_set = creds.get("configuration_set") or None

    def _build_client(self):
        return boto3.client(
            "ses",
            region_name=self._region,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    def _build_raw_message(self, message: EmailMessage) -> bytes:
        """Compose an RFC822 message including custom Message-ID header."""
        message = self._prepare_message(message)

        mime = MimeMessage()
        mime["Subject"] = message.subject
        mime["From"] = formataddr((message.from_name or "", message.from_email))
        mime["To"] = formataddr((message.to_name or "", message.to_email))
        if message.reply_to:
            mime["Reply-To"] = message.reply_to

        # Custom headers (e.g. Message-ID for In-Reply-To matching, List-Unsubscribe)
        for name, value in (message.headers or {}).items():
            if value is None:
                continue
            # Avoid duplicating headers we set explicitly above
            if name.lower() in {"subject", "from", "to", "reply-to"}:
                continue
            mime[name] = value

        if message.text_content and message.html_content:
            mime.set_content(message.text_content)
            mime.add_alternative(message.html_content, subtype="html")
        elif message.html_content:
            mime.set_content(message.html_content, subtype="html")
        else:
            mime.set_content(message.text_content or "")

        return mime.as_bytes()

    def _send_raw_sync(self, raw: bytes, source: str, destination: str) -> dict:
        """Synchronous boto3 call — wrapped via run_in_executor."""
        kwargs: dict = {
            "Source": source,
            "Destinations": [destination],
            "RawMessage": {"Data": raw},
        }
        if self._configuration_set:
            kwargs["ConfigurationSetName"] = self._configuration_set
        return self._build_client().send_raw_email(**kwargs)

    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email via AWS SES."""
        prepared = self._prepare_message(message)
        try:
            raw = self._build_raw_message(message)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                self._send_raw_sync,
                raw,
                prepared.from_email,
                prepared.to_email,
            )
            ses_message_id = response.get("MessageId")
            logger.info(
                "AWS SES: E-Mail gesendet an {email} (id={id})",
                email=prepared.to_email,
                id=ses_message_id,
            )
            return SendResult(success=True, message_id=ses_message_id)
        except NoCredentialsError as e:
            logger.error("AWS SES: Credentials fehlen oder ungültig")
            return SendResult(success=False, error=f"AWS credentials error: {e}")
        except ClientError as e:
            err = e.response.get("Error", {})
            code = err.get("Code", "Unknown")
            msg = err.get("Message", str(e))
            logger.error("AWS SES Fehler {code}: {msg}", code=code, msg=msg)
            return SendResult(
                success=False,
                error=f"AWS SES {code}: {msg}",
                provider_response=e.response,
            )
        except Exception as e:
            logger.exception("AWS SES: Unerwarteter Fehler")
            return SendResult(success=False, error=str(e))

    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 14
    ) -> list[SendResult]:
        """Send multiple emails concurrently within SES rate limits.

        SES sandbox accounts are throttled at 1 email/sec, production starts
        at 14/sec and ramps up. Default batch_size matches the ramp-start.
        """
        results: list[SendResult] = []
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            tasks = [self.send_email(msg) for msg in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in batch_results:
                if isinstance(result, BaseException):
                    results.append(SendResult(success=False, error=str(result)))
                else:
                    results.append(result)
            if i + batch_size < len(messages):
                await asyncio.sleep(1.0)
        return results

    async def verify_credentials(self) -> bool:
        """Verify AWS SES credentials by calling get_send_quota."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._build_client().get_send_quota)
            return True
        except (ClientError, NoCredentialsError, ValueError) as e:
            logger.error("AWS SES Verifizierung fehlgeschlagen: {err}", err=str(e))
            return False
        except Exception as e:
            logger.exception("AWS SES verify_credentials: Unerwarteter Fehler")
            logger.error("Details: {err}", err=str(e))
            return False
