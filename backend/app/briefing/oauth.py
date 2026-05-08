"""Briefing OAuth — re-exports from shared integrations.oauth layer.

All implementations live in app.integrations.oauth now.
This module re-exports for backwards compatibility with existing briefing code.
"""

from app.integrations.oauth import (
    decrypt_token,
    encrypt_token,
    refresh_google_token,
    refresh_microsoft_token,
)

__all__ = [
    "decrypt_token",
    "encrypt_token",
    "refresh_google_token",
    "refresh_microsoft_token",
]
