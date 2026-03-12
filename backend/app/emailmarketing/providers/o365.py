"""Office 365 / Microsoft Graph email provider implementation."""

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

GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


class O365Provider(EmailProvider):
    """Office 365 / Microsoft Graph email provider.

    Requires an access token with Mail.Send permission.
    The api_key_encrypted field should contain the access token.
    """

    def __init__(self, config: "EmailProviderModel") -> None:
        super().__init__(config)
        # Decrypt the OAuth access token
        self.access_token = decrypt_api_key(config.api_key_encrypted or "")

    def _get_headers(self) -> dict:
        """Get authorization headers for Graph API."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, message: EmailMessage) -> dict:
        """Build Microsoft Graph API payload from message."""
        message = self._prepare_message(message)

        payload = {
            "message": {
                "subject": message.subject,
                "body": {
                    "contentType": "HTML",
                    "content": message.html_content,
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": message.to_email,
                        }
                    }
                ],
                "from": {
                    "emailAddress": {
                        "address": message.from_email,
                        "name": message.from_name,
                    }
                },
            },
            "saveToSentItems": False,
        }

        # Add recipient name if provided
        if message.to_name:
            payload["message"]["toRecipients"][0]["emailAddress"]["name"] = message.to_name

        # Add reply-to
        if message.reply_to:
            payload["message"]["replyTo"] = [
                {"emailAddress": {"address": message.reply_to}}
            ]

        # Add tracking token as custom header
        if message.tracking_token:
            payload["message"]["internetMessageHeaders"] = [
                {"name": "X-Tracking-Token", "value": message.tracking_token}
            ]

        return payload

    async def send_email(self, message: EmailMessage) -> SendResult:
        """Send a single email via Microsoft Graph API."""
        try:
            async with httpx.AsyncClient() as client:
                # Send mail endpoint
                response = await client.post(
                    f"{GRAPH_API_URL}/users/{self.sender_email}/sendMail",
                    headers=self._get_headers(),
                    json=self._build_payload(message),
                    timeout=30.0,
                )

                if response.status_code == 202:
                    # Microsoft Graph returns 202 Accepted for sendMail
                    logger.info(
                        "O365: E-Mail gesendet an {email}",
                        email=message.to_email,
                    )
                    return SendResult(
                        success=True,
                        # Graph API doesn't return message ID on sendMail
                        message_id=None,
                    )
                else:
                    error_body = response.text
                    logger.error(
                        "O365 Fehler: {status} - {body}",
                        status=response.status_code,
                        body=error_body,
                    )
                    return SendResult(
                        success=False,
                        error=f"Graph API error: {response.status_code}",
                        provider_response={"status": response.status_code, "body": error_body},
                    )

        except httpx.TimeoutException:
            logger.error("O365: Timeout beim Senden")
            return SendResult(success=False, error="Request timeout")
        except Exception as e:
            logger.exception("O365: Unerwarteter Fehler")
            return SendResult(success=False, error=str(e))

    async def send_batch(
        self, messages: list[EmailMessage], batch_size: int = 20
    ) -> list[SendResult]:
        """Send multiple emails via Microsoft Graph.

        Graph API supports $batch endpoint, but for simplicity we send
        individually with limited concurrency (Microsoft has stricter limits).
        """
        results = []

        # Microsoft has stricter rate limits, use smaller batches
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

            # Longer delay for Microsoft to avoid throttling
            if i + batch_size < len(messages):
                await asyncio.sleep(1.0)

        return results

    async def verify_credentials(self) -> bool:
        """Verify Microsoft Graph API credentials."""
        try:
            async with httpx.AsyncClient() as client:
                # Try to get user profile to verify token
                response = await client.get(
                    f"{GRAPH_API_URL}/me",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("O365 Verifizierung fehlgeschlagen: {err}", err=str(e))
            return False
