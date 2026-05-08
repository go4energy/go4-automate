"""Shared OAuth utilities — token encryption, refresh, code exchange, email fetch.

Extracted from app.briefing.oauth and app.briefing.router so that
both the briefing and assistant modules can use them without cross-coupling.
"""

import json
from base64 import b64encode

import httpx

from app.config import settings

# ---------------------------------------------------------------------------
# Token encryption / decryption
# ---------------------------------------------------------------------------


def _get_fernet_key() -> bytes:
    """Derive a Fernet-compatible key from the app secret key."""
    import hashlib

    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    return b64encode(key_bytes)


def encrypt_token(token_data: dict) -> str:
    """Encrypt OAuth token data for storage in DB."""
    from cryptography.fernet import Fernet

    f = Fernet(_get_fernet_key())
    payload = json.dumps(token_data).encode()
    return f.encrypt(payload).decode()


def decrypt_token(encrypted: str) -> dict:
    """Decrypt stored OAuth token data."""
    from cryptography.fernet import Fernet

    f = Fernet(_get_fernet_key())
    payload = f.decrypt(encrypted.encode())
    return json.loads(payload)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


async def refresh_google_token(
    refresh_token: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """Refresh a Google OAuth2 access token."""
    cid = client_id or settings.google_client_id
    csecret = client_secret or settings.google_client_secret

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": cid,
                "client_secret": csecret,
            },
        )
        resp.raise_for_status()
    return resp.json()


async def refresh_microsoft_token(
    refresh_token: str,
    client_id: str | None = None,
    client_secret: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """Refresh a Microsoft OAuth2 access token."""
    cid = client_id or settings.microsoft_client_id
    csecret = client_secret or settings.microsoft_client_secret
    tid = tenant_id or settings.microsoft_tenant_id or "common"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": cid,
                "client_secret": csecret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# OAuth code exchange
# ---------------------------------------------------------------------------


def oauth_scope(provider: str, integration_type: str | None = None) -> str:
    """Return provider scopes for source or personal integrations."""
    if provider == "microsoft":
        if integration_type == "email":
            return "Mail.Read User.Read offline_access"
        if integration_type == "calendar":
            return "Calendars.Read User.Read offline_access"
        return "Calendars.Read Mail.Read User.Read offline_access"

    if integration_type == "email":
        return "https://www.googleapis.com/auth/gmail.readonly openid email"
    if integration_type == "calendar":
        return "https://www.googleapis.com/auth/calendar.readonly openid email"
    return (
        "https://www.googleapis.com/auth/calendar.readonly "
        "https://www.googleapis.com/auth/gmail.readonly "
        "openid email"
    )


async def exchange_oauth_code(
    code: str,
    provider: str,
    callback_url: str,
    integration_type: str | None = None,
) -> dict:
    """Exchange an OAuth code for access and refresh tokens."""
    scope = oauth_scope(provider, integration_type)

    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "microsoft":
            tid = settings.microsoft_tenant_id or "common"
            response = await client.post(
                f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.microsoft_client_id,
                    "client_secret": settings.microsoft_client_secret,
                    "code": code,
                    "redirect_uri": callback_url,
                    "scope": scope,
                },
            )
        else:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "redirect_uri": callback_url,
                },
            )

        response.raise_for_status()
        return response.json()


async def fetch_oauth_email(access_token: str, provider: str) -> str:
    """Fetch the primary email address for the connected account."""
    async with httpx.AsyncClient(timeout=30) as client:
        if provider == "microsoft":
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            me = response.json()
            return me.get("mail") or me.get("userPrincipalName", "")

        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json().get("email", "")
