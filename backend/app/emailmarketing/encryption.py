"""API Key encryption using Fernet symmetric encryption.

Environment Variables:
    EMAIL_ENCRYPTION_KEY      - 32-byte base64-encoded key for Fernet.
                                Generate via:
                                python -m app.emailmarketing.encryption
    REQUIRE_ENCRYPTION_KEYS   - When set to "true"/"1" the app refuses to
                                operate without an encryption key. Set this
                                in production. In dev (default) we degrade
                                to plaintext storage with a loud warning so
                                local setup stays frictionless.

Behaviour:
- REQUIRE_ENCRYPTION_KEYS=true + key missing → raises RuntimeError on first
  encrypt/decrypt call (loud failure, prevents silent plaintext leak).
- REQUIRE_ENCRYPTION_KEYS=false (default) + key missing → logs a one-time
  warning at logger.error level and returns None (existing behaviour
  preserved for dev systems).
"""

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

# Prefix to identify encrypted values
ENCRYPTED_PREFIX = "enc::"


def _require_keys() -> bool:
    """True when the platform should refuse plaintext-fallback storage."""
    return os.getenv("REQUIRE_ENCRYPTION_KEYS", "").lower() in {"1", "true", "yes"}


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet | None:
    """Get Fernet instance, cached for performance."""
    key = os.getenv("EMAIL_ENCRYPTION_KEY")

    if not key:
        if _require_keys():
            raise RuntimeError(
                "EMAIL_ENCRYPTION_KEY ist nicht gesetzt und "
                "REQUIRE_ENCRYPTION_KEYS=true. API-Keys dürfen nicht im "
                "Klartext gespeichert werden. Setze EMAIL_ENCRYPTION_KEY "
                "(generieren via `python -m app.emailmarketing.encryption`)."
            )
        logger.error(
            "⚠️  EMAIL_ENCRYPTION_KEY nicht gesetzt — API-Keys werden im "
            "Klartext gespeichert. Setze REQUIRE_ENCRYPTION_KEYS=true in "
            "Production, um diesen Fallback zu deaktivieren."
        )
        return None

    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error("Ungültiger EMAIL_ENCRYPTION_KEY: {err}", err=str(e))
        if _require_keys():
            raise RuntimeError(
                f"Ungültiger EMAIL_ENCRYPTION_KEY und REQUIRE_ENCRYPTION_KEYS=true: {e}"
            ) from e
        return None


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key.

    Args:
        plaintext: The plain API key

    Returns:
        Encrypted string with 'enc::' prefix, or plaintext if encryption unavailable
    """
    if not plaintext:
        return plaintext

    # Already encrypted?
    if plaintext.startswith(ENCRYPTED_PREFIX):
        return plaintext

    fernet = _get_fernet()
    if not fernet:
        return plaintext

    try:
        encrypted = fernet.encrypt(plaintext.encode())
        return f"{ENCRYPTED_PREFIX}{encrypted.decode()}"
    except Exception as e:
        logger.error("Verschlüsselung fehlgeschlagen: {err}", err=str(e))
        return plaintext


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key.

    Args:
        encrypted: The encrypted API key (with 'enc::' prefix)

    Returns:
        Decrypted plaintext, or the input if not encrypted/decryption fails
    """
    if not encrypted:
        return encrypted

    # Not encrypted?
    if not encrypted.startswith(ENCRYPTED_PREFIX):
        return encrypted

    fernet = _get_fernet()
    if not fernet:
        logger.warning("Kann verschlüsselten Key nicht entschlüsseln - kein Key gesetzt")
        return encrypted

    try:
        encrypted_data = encrypted[len(ENCRYPTED_PREFIX) :]
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("Entschlüsselung fehlgeschlagen - ungültiger Token")
        return encrypted
    except Exception as e:
        logger.error("Entschlüsselung fehlgeschlagen: {err}", err=str(e))
        return encrypted


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted."""
    return value.startswith(ENCRYPTED_PREFIX) if value else False


def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key.

    Usage:
        key = generate_encryption_key()
        # Add to .env: EMAIL_ENCRYPTION_KEY=<key>
    """
    return Fernet.generate_key().decode()


# Convenience function for CLI
if __name__ == "__main__":
    print("Neuer Encryption Key:")
    print(generate_encryption_key())
