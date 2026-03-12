"""Mailgun email provider implementation."""

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


class MailgunProvider(EmailProvider):
    """Mailgun email provider."""

    def __init__(self, config: "EmailProviderModel") -> None:
        super().__init__(config)
        # Decrypt API key
        self.api_key = decrypt_api_key(config.api_key_encrypted or "")

        # Extract domain from sender email
        self.domain = self._extract_domain(config.sender_email)
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}"

    def _extract_domain(self, email: str) -> str:
        """Extract domain from email address."""
        return email.split("@")[1] if "@" in email else email

    def _get_auth(self) -> tuple[str, str]:
        """Get basic auth credentials for Mailgun API."""
        return ("api", self.api_key)

    def _build_form_data(self, message: EmailMessage) -> dict:
        """Build Mailgun form data from message."""
        message = self._prepare_message(message)

        data = {
            "from": f"{message.from_name} <{message.from_email}>",
            "to": message.to_email,
            "subject": message.subject,
            "html": message.html_content,
        }

        if message.to_name:
            data["to"] = f"{message.to_name} <{message.to_email}>"

        if message.text_content:
            data["text"] = message.text_content

        if message.reply_to:
            data["h:Reply-To"] = message.reply_to

        # Add tracking token as custom variable
        if message.tracking_token:
            data["v:tracking_token"] = message.tracking_token

        # Add custom headers
        for key, value in message.headers.items():
            data[f"h:{key}"] = value

        return data

    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email via Mailgun."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/messages",
                    auth=self._get_auth(),
                    data=self._build_form_data(message),
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    message_id = data.get("id")
                    logger.info(
                        "Mailgun: E-Mail gesendet an {email}",
                        email=message.to_email,
                    )
                    return SendResult(
                        success=True,
                        message_id=message_id,
                        provider_response=data,
                    )
                else:
                    error_body = response.text
                    logger.error(
                        "Mailgun Fehler: {status} - {body}",
                        status=response.status_code,
                        body=error_body,
                    )
                    return SendResult(
                        success=False,
                        error=f"Mailgun API error: {response.status_code}",
                        provider_response={"status": response.status_code, "body": error_body},
                    )

        except httpx.TimeoutException:
            logger.error("Mailgun: Timeout beim Senden")
            return SendResult(success=False, error="Request timeout")
        except Exception as e:
            logger.exception("Mailgun: Unerwarteter Fehler")
            return SendResult(success=False, error=str(e))

    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 100
    ) -> list[SendResult]:
        """Send multiple emails via Mailgun.

        Mailgun supports batch sending via recipient variables,
        but for simplicity we send individually with concurrency.
        """
        results = []

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

            # Small delay between batches
            if i + batch_size < len(messages):
                await asyncio.sleep(0.5)

        return results

    async def verify_credentials(self) -> bool:
        """Verify Mailgun API credentials."""
        try:
            async with httpx.AsyncClient() as client:
                # Use domain info endpoint to verify
                response = await client.get(
                    f"https://api.mailgun.net/v3/domains/{self.domain}",
                    auth=self._get_auth(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Mailgun Verifizierung fehlgeschlagen: {err}", err=str(e))
            return False
