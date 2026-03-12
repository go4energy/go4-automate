"""Access Token encryption using Fernet symmetric encryption.

Environment Variables:
    WHATSAPP_ENCRYPTION_KEY - 32-byte base64-encoded key for Fernet
                              Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If no key is set, a warning is logged and tokens are stored in plaintext (development mode).
"""

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

# Prefix to identify encrypted values
ENCRYPTED_PREFIX = "enc::"


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet | None:
    """Get Fernet instance, cached for performance."""
    key = os.getenv("WHATSAPP_ENCRYPTION_KEY")

    if not key:
        logger.warning(
            "WHATSAPP_ENCRYPTION_KEY nicht gesetzt - Access Tokens werden im Klartext gespeichert!"
        )
        return None

    try:
        return Fernet(key.encode())
    except Exception as e:
        logger.error("Ungültiger WHATSAPP_ENCRYPTION_KEY: {err}", err=str(e))
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
