"""Contact-level utilities shared across modules.

The tracking hash is a 12-char alphanumeric string stored in
``contacts.tracking_hash`` (partial UNIQUE index where NOT NULL). It is the
canonical platform-wide identifier embedded into outreach URLs so the
customer-journey tracking router can resolve a landing-page hit back to a
specific contact.

Hash generation lives here so leadgen, customer_journey and any future
caller stay in sync — previously the same logic had two duplicate copies in
``customer_journey/service.py`` and ``customer_journey/import_service.py``.
"""

from __future__ import annotations

import secrets
import string

_TRACKING_HASH_ALPHABET = string.ascii_letters + string.digits


def generate_tracking_hash(length: int = 12) -> str:
    """Return a cryptographically random alphanumeric hash of ``length`` chars.

    With 62 chars × 12 positions the collision probability is ~10⁻²¹ at the
    1M-contact scale, so we don't bother retrying — the partial UNIQUE index
    on ``contacts.tracking_hash`` is the safety net.
    """
    return "".join(secrets.choice(_TRACKING_HASH_ALPHABET) for _ in range(length))
