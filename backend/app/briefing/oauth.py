"""Briefing OAuth — token encryption and provider helpers for Calendar/Email sources."""

import json
from base64 import b64encode

from app.config import settings


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


async def refresh_google_token(
    refresh_token: str,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> dict:
    """Refresh a Google OAuth2 access token."""
    import httpx

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
    import httpx

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
