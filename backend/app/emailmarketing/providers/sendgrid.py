"""SendGrid email provider implementation."""

import asyncio
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from app.emailmarketing.encryption import decrypt_api_key
from app.emailmarketing.providers.base import (
    EmailMessage,
    EmailProvider,
    SendResult,
)

if TYPE_CHECKING:
    from app.emailmarketing.models import EmailProvider as EmailProviderModel

SENDGRID_API_URL = "https://api.sendgrid.com/v3"


class SendGridProvider(EmailProvider):
    """SendGrid email provider using API v3."""

    def __init__(self, config: "EmailProviderModel") -> None:
        super().__init__(config)
        # Decrypt API key
        self.api_key = decrypt_api_key(config.api_key_encrypted or "")

    def _get_headers(self) -> dict:
        """Get authorization headers for SendGrid API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, message: EmailMessage) -> dict:
        """Build SendGrid API payload from message."""
        message = self._prepare_message(message)

        payload = {
            "personalizations": [
                {
                    "to": [{"email": message.to_email}],
                }
            ],
            "from": {
                "email": message.from_email,
                "name": message.from_name,
            },
            "subject": message.subject,
            "content": [],
        }

        # Add recipient name if provided
        if message.to_name:
            payload["personalizations"][0]["to"][0]["name"] = message.to_name

        # Add reply-to
        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}

        # Add content
        if message.text_content:
            payload["content"].append(
                {"type": "text/plain", "value": message.text_content}
            )
        payload["content"].append({"type": "text/html", "value": message.html_content})

        # Add custom headers
        if message.headers:
            payload["headers"] = message.headers

        # Add tracking token as custom arg for webhooks
        if message.tracking_token:
            payload["custom_args"] = {"tracking_token": message.tracking_token}

        return payload

    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email via SendGrid."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SENDGRID_API_URL}/mail/send",
                    headers=self._get_headers(),
                    json=self._build_payload(message),
                    timeout=30.0,
                )

                if response.status_code in (200, 202):
                    # SendGrid returns message ID in X-Message-Id header
                    message_id = response.headers.get("X-Message-Id")
                    logger.info(
                        "SendGrid: E-Mail gesendet an {email}",
                        email=message.to_email,
                    )
                    return SendResult(
                        success=True,
                        message_id=message_id,
                    )
                else:
                    error_body = response.text
                    logger.error(
                        "SendGrid Fehler: {status} - {body}",
                        status=response.status_code,
                        body=error_body,
                    )
                    return SendResult(
                        success=False,
                        error=f"SendGrid API error: {response.status_code}",
                        provider_response={"status": response.status_code, "body": error_body},
                    )

        except httpx.TimeoutException:
            logger.error("SendGrid: Timeout beim Senden")
            return SendResult(success=False, error="Request timeout")
        except Exception as e:
            logger.exception("SendGrid: Unerwarteter Fehler")
            return SendResult(success=False, error=str(e))

    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 100
    ) -> list[SendResult]:
        """Send multiple emails via SendGrid.

        SendGrid doesn't have a true batch endpoint, so we send concurrently
        with rate limiting.
        """
        results = []

        # Process in batches to respect rate limits
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]

            # Send batch concurrently
            tasks = [self.send_email(msg) for msg in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    results.append(SendResult(success=False, error=str(result)))
                else:
                    results.append(result)

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(messages):
                await asyncio.sleep(0.5)

        return results

    async def verify_credentials(self) -> bool:
        """Verify SendGrid API credentials."""
        try:
            async with httpx.AsyncClient() as client:
                # Use scopes endpoint to verify credentials
                response = await client.get(
                    f"{SENDGRID_API_URL}/scopes",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("SendGrid Verifizierung fehlgeschlagen: {err}", err=str(e))
            return False
