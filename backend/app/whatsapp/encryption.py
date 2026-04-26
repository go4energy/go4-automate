"""Access Token encryption using Fernet symmetric encryption.

Environment Variables:
    WHATSAPP_ENCRYPTION_KEY  - 32-byte base64-encoded key for Fernet.
                               Generate via: python -m app.whatsapp.encryption
    REQUIRE_ENCRYPTION_KEYS  - When set to "true"/"1" the app refuses to
                               operate without an encryption key. Set this
                               in production. In dev (default) we degrade
                               to plaintext storage with a loud warning.
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
    key = os.getenv("WHATSAPP_ENCRYPTION_KEY")

    if not key:
        if _require_keys():
            raise RuntimeError(
                "WHATSAPP_ENCRYPTION_KEY ist nicht gesetzt und "
                "REQUIRE_ENCRYPTION_KEYS=true. Access Tokens dürfen nicht im "
                "Klartext gespeichert werden. Setze WHATSAPP_ENCRYPTION_KEY "
                "(generieren via `python -m app.whatsapp.encryption`)."
            )
        logger.error(
            "⚠️  WHATSAPP_ENCRYPTION_KEY nicht gesetzt — Access Tokens werden "
            "im Klartext gespeichert. Setze REQUIRE_ENCRYPTION_KEYS=true in "
            "Production, um diesen Fallback zu deaktivieren."
        )
        return None

    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error("Ungültiger WHATSAPP_ENCRYPTION_KEY: {err}", err=str(e))
        if _require_keys():
            raise RuntimeError(
                f"Ungültiger WHATSAPP_ENCRYPTION_KEY und REQUIRE_ENCRYPTION_KEYS=true: {e}"
            ) from e
        return None


def encrypt_access_token(plaintext: str) -> str:
    """Encrypt an access token.

    Args:
        plaintext: The plain access token

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


def decrypt_access_token(encrypted: str) -> str:
    """Decrypt an access token.

    Args:
        encrypted: The encrypted access token (with 'enc::' prefix)

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
        logger.warning(
            "Kann verschlüsselten Token nicht entschlüsseln - kein Key gesetzt"
        )
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
        # Add to .env: WHATSAPP_ENCRYPTION_KEY=<key>
    """
    return Fernet.generate_key().decode()


# Convenience function for CLI
if __name__ == "__main__":
    print("Neuer Encryption Key:")
    print(generate_encryption_key())
