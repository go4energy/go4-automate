"""Hashing utilities for Meta Conversion API."""

import hashlib


def hash_for_meta(value: str | None) -> str | None:
    """Hash a value with SHA256 for Meta Conversion API.

    Meta requires SHA256-hashed, lowercase hex-encoded user data.
    Email: lowercase, trimmed, then SHA256.
    """
    if not value:
        return None
    cleaned = value.strip().lower()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def hash_phone(phone: str | None) -> str | None:
    """Hash a phone number for Meta Conversion API.

    Phone: digits only with country code (49 for Germany), then SHA256.
    """
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit())
    if not digits.startswith("49"):
        digits = "49" + digits.lstrip("0")
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()
