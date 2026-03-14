"""Auth helpers for Microsoft Graph."""

from urllib.parse import quote, urlencode

from app.config import settings


class MicrosoftGraphAuthService:
    """Build OAuth URLs and token requests for Microsoft Graph."""

    @staticmethod
    def build_authorize_url(
        *,
        state: str,
        redirect_uri: str,
        scopes: list[str],
    ) -> str:
        """Create the delegated OAuth authorization URL."""
        tenant = settings.microsoft_tenant_id or "common"
        params = urlencode(
            {
                "client_id": settings.microsoft_client_id,
                "response_type": "code",
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state,
            },
            quote_via=quote,
        )
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{params}"

    @staticmethod
    def token_url() -> str:
        """Return the configured Microsoft Graph token endpoint."""
        tenant = settings.microsoft_tenant_id or "common"
        return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
