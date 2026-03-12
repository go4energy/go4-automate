"""Meta Graph API client for WhatsApp Cloud API.

Documentation: https://developers.facebook.com/docs/whatsapp/cloud-api
"""

from datetime import datetime
from typing import Any

import httpx
from loguru import logger

from app.whatsapp.encryption import decrypt_access_token

# Meta Graph API base URL
GRAPH_API_BASE = "https://graph.facebook.com/v18.0"


class MetaAPIError(Exception):
    """Error from Meta Graph API."""

    def __init__(
        self, message: str, code: int | None = None, subcode: int | None = None
    ):
        self.message = message
        self.code = code
        self.subcode = subcode
        super().__init__(message)


class MetaWhatsAppClient:
    """Client for Meta WhatsApp Cloud API."""

    def __init__(
        self,
        phone_number_id: str,
        access_token_encrypted: str,
        waba_id: str | None = None,
    ):
        """Initialize the client.

        Args:
            phone_number_id: Meta Phone Number ID
            access_token_encrypted: Encrypted or plain access token
            waba_id: WhatsApp Business Account ID (for template operations)
        """
        self.phone_number_id = phone_number_id
        self.access_token = decrypt_access_token(access_token_encrypted)
        self.waba_id = waba_id
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=GRAPH_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response and raise errors if needed."""
        try:
            data = response.json()
        except Exception:
            response.raise_for_status()
            return {}

        if "error" in data:
            error = data["error"]
            raise MetaAPIError(
                message=error.get("message", "Unknown error"),
                code=error.get("code"),
                subcode=error.get("error_subcode"),
            )

        response.raise_for_status()
        return data

    # ==================== Message Operations ====================

    async def send_text_message(
        self,
        to: str,
        body: str,
        preview_url: bool = False,
    ) -> str:
        """Send a text message.

        Args:
            to: Recipient phone number (with country code, no +)
            body: Message text
            preview_url: Whether to show URL previews

        Returns:
            wamid (WhatsApp Message ID)
        """
        client = await self._get_client()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body, "preview_url": preview_url},
        }

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        data = await self._handle_response(response)

        wamid = data.get("messages", [{}])[0].get("id")
        logger.info(
            "WhatsApp Nachricht gesendet an {to}: {wamid}",
            to=to,
            wamid=wamid,
        )
        return wamid

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "de",
        components: list[dict] | None = None,
    ) -> str:
        """Send a template message.

        Args:
            to: Recipient phone number
            template_name: Name of the approved template
            language_code: Template language code
            components: Template components with parameters

        Returns:
            wamid (WhatsApp Message ID)
        """
        client = await self._get_client()

        template_data: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if components:
            template_data["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template_data,
        }

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        data = await self._handle_response(response)

        wamid = data.get("messages", [{}])[0].get("id")
        logger.info(
            "WhatsApp Template '{template}' gesendet an {to}: {wamid}",
            template=template_name,
            to=to,
            wamid=wamid,
        )
        return wamid

    async def send_media_message(
        self,
        to: str,
        media_type: str,
        media_url: str | None = None,
        media_id: str | None = None,
        caption: str | None = None,
        filename: str | None = None,
    ) -> str:
        """Send a media message (image, document, audio, video).

        Args:
            to: Recipient phone number
            media_type: Type of media (image, document, audio, video)
            media_url: URL of the media (either url or id required)
            media_id: Meta Media ID (either url or id required)
            caption: Optional caption
            filename: Filename for documents

        Returns:
            wamid (WhatsApp Message ID)
        """
        client = await self._get_client()

        media_data: dict[str, Any] = {}
        if media_url:
            media_data["link"] = media_url
        elif media_id:
            media_data["id"] = media_id
        else:
            raise ValueError("Either media_url or media_id is required")

        if caption:
            media_data["caption"] = caption
        if filename and media_type == "document":
            media_data["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": media_type,
            media_type: media_data,
        }

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        data = await self._handle_response(response)

        wamid = data.get("messages", [{}])[0].get("id")
        logger.info(
            "WhatsApp {media_type} gesendet an {to}: {wamid}",
            media_type=media_type,
            to=to,
            wamid=wamid,
        )
        return wamid

    async def mark_as_read(self, wamid: str) -> bool:
        """Mark a message as read.

        Args:
            wamid: WhatsApp Message ID

        Returns:
            Success status
        """
        client = await self._get_client()

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": wamid,
        }

        response = await client.post(
            f"/{self.phone_number_id}/messages",
            json=payload,
        )
        data = await self._handle_response(response)
        return data.get("success", False)

    # ==================== Template Operations ====================

    async def get_templates(self) -> list[dict]:
        """Fetch all templates from Meta.

        Returns:
            List of template objects
        """
        if not self.waba_id:
            raise ValueError("waba_id is required for template operations")

        client = await self._get_client()

        templates = []
        url = f"/{self.waba_id}/message_templates"
        params: dict[str, str] = {"limit": "100"}

        while url:
            response = await client.get(url, params=params)
            data = await self._handle_response(response)

            templates.extend(data.get("data", []))

            # Handle pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # Next URL includes params

        logger.info("Fetched {count} templates from Meta", count=len(templates))
        return templates

    async def get_template(self, template_name: str) -> dict | None:
        """Get a specific template by name.

        Args:
            template_name: Name of the template

        Returns:
            Template object or None
        """
        templates = await self.get_templates()
        for template in templates:
            if template.get("name") == template_name:
                return template
        return None

    # ==================== Verification ====================

    async def verify_credentials(self) -> dict:
        """Verify the credentials are valid.

        Returns:
            Phone number info if valid
        """
        client = await self._get_client()

        response = await client.get(
            f"/{self.phone_number_id}",
            params={
                "fields": "verified_name,code_verification_status,display_phone_number"
            },
        )
        data = await self._handle_response(response)

        logger.info(
            "WhatsApp Credentials verifiziert: {name}",
            name=data.get("verified_name"),
        )
        return data

    # ==================== Utility Functions ====================


def normalize_phone_number(phone: str) -> str:
    """Normalize phone number for WhatsApp API.

    Removes +, spaces, dashes and other formatting.
    WhatsApp expects format: country code + number without +

    Args:
        phone: Phone number in any format

    Returns:
        Normalized phone number
    """
    # Remove common formatting
    normalized = (
        phone.replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    # Remove leading zeros (but keep country code)
    if normalized.startswith("00"):
        normalized = normalized[2:]

    return normalized


def format_template_variables(
    template_components: list[dict],
    variables: dict[str, str],
) -> list[dict]:
    """Format template variables for API call.

    Args:
        template_components: Template component definitions from Meta
        variables: Dictionary of variable values {variable_name: value}

    Returns:
        Formatted components for API call
    """
    result = []

    for component in template_components:
        comp_type = component.get("type", "").upper()

        if comp_type in ("HEADER", "BODY"):
            # Check if component has parameters
            if "example" in component or "{{" in component.get("text", ""):
                params = []
                # Extract variable names and map to values
                text = component.get("text", "")
                param_count = text.count("{{")

                for i in range(1, param_count + 1):
                    var_name = f"var{i}"
                    # Try to find matching variable
                    value = variables.get(var_name, variables.get(str(i), ""))
                    params.append({"type": "text", "text": str(value)})

                if params:
                    result.append(
                        {
                            "type": comp_type.lower(),
                            "parameters": params,
                        }
                    )

        elif comp_type == "BUTTON":
            # Handle button parameters (URL buttons with variables)
            buttons = component.get("buttons", [])
            for idx, button in enumerate(buttons):
                if button.get("type") == "URL" and "{{" in button.get("url", ""):
                    var_name = f"button_{idx + 1}"
                    value = variables.get(var_name, "")
                    result.append(
                        {
                            "type": "button",
                            "sub_type": "url",
                            "index": str(idx),
                            "parameters": [{"type": "text", "text": str(value)}],
                        }
                    )

    return result


def calculate_window_expiry(last_customer_message: datetime) -> datetime:
    """Calculate when the 24h service window expires.

    Args:
        last_customer_message: Timestamp of last customer message

    Returns:
        Window expiry datetime
    """
    from datetime import timedelta

    return last_customer_message + timedelta(hours=24)


def is_window_open(window_expires_at: datetime | None) -> bool:
    """Check if the 24h service window is still open.

    Args:
        window_expires_at: Window expiry datetime

    Returns:
        True if window is open
    """
    if not window_expires_at:
        return False
    return datetime.utcnow() < window_expires_at
