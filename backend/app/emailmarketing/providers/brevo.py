"""Brevo (formerly Sendinblue) email provider implementation.

EU-hosted (Paris), GDPR-friendly. Standard REST API at v3.

API: https://developers.brevo.com/reference/sendtransacemail

Authentication: ``api-key`` header (single-key, like SendGrid).

We use the ``headers`` field on the transactional send payload to inject
our custom RFC822 ``Message-ID`` header, so the inbound reply-poller can
match replies via ``In-Reply-To`` / ``References``.
"""

from __future__ import annotations

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

BREVO_API_URL = "https://api.brevo.com/v3"


class BrevoProvider(EmailProvider):
    """Brevo (Sendinblue) email provider using the v3 transactional API."""

    def __init__(self, config: EmailProviderModel) -> None:
        super().__init__(config)
        self.api_key = decrypt_api_key(config.api_key_encrypted or "")

    def _get_headers(self) -> dict:
        return {
            "api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def _build_payload(self, message: EmailMessage) -> dict:
        message = self._prepare_message(message)

        sender: dict = {"email": message.from_email}
        if message.from_name:
            sender["name"] = message.from_name

        recipient: dict = {"email": message.to_email}
        if message.to_name:
            recipient["name"] = message.to_name

        payload: dict = {
            "sender": sender,
            "to": [recipient],
            "subject": message.subject,
        }

        if message.html_content:
            payload["htmlContent"] = message.html_content
        if message.text_content:
            payload["textContent"] = message.text_content
        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to}

        # Custom headers (Message-ID for In-Reply-To matching, List-Unsubscribe, etc.)
        # Brevo expects {"name": value} flat-mapped under "headers".
        if message.headers:
            clean_headers = {
                k: v for k, v in message.headers.items() if v is not None
            }
            if clean_headers:
                payload["headers"] = clean_headers

        # tracking_token surfaces back via webhooks for click/open events
        if message.tracking_token:
            payload["params"] = {"tracking_token": message.tracking_token}

        return payload

    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email via Brevo."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{BREVO_API_URL}/smtp/email",
                    headers=self._get_headers(),
                    json=self._build_payload(message),
                    timeout=30.0,
                )

                if response.status_code in (200, 201, 202):
                    body = response.json() if response.content else {}
                    msg_id = body.get("messageId")
                    logger.info(
                        "Brevo: E-Mail gesendet an {email} (id={id})",
                        email=message.to_email,
                        id=msg_id,
                    )
                    return SendResult(success=True, message_id=msg_id)

                error_body = response.text
                logger.error(
                    "Brevo Fehler: {status} - {body}",
                    status=response.status_code,
                    body=error_body[:500],
                )
                return SendResult(
                    success=False,
                    error=f"Brevo API error: {response.status_code}",
                    provider_response={
                        "status": response.status_code,
                        "body": error_body,
                    },
                )

        except httpx.TimeoutException:
            logger.error("Brevo: Timeout beim Senden")
            return SendResult(success=False, error="Request timeout")
        except Exception as e:
            logger.exception("Brevo: Unerwarteter Fehler")
            return SendResult(success=False, error=str(e))

    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 30
    ) -> list[SendResult]:
        """Send multiple emails concurrently with batch throttling.

        Brevo allows ~30 req/s on Pay-As-You-Go and higher on paid plans.
        We default to 30 concurrent and pause briefly between batches.
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
                await asyncio.sleep(0.5)
        return results

    async def verify_credentials(self) -> bool:
        """Verify Brevo API credentials by calling /account."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BREVO_API_URL}/account",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Brevo Verifizierung fehlgeschlagen: {err}", err=str(e))
            return False
