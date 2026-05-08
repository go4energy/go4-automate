"""Gender detection for leadgen contacts.

Two-stage approach:

1. ``gender_guesser`` library — offline, deterministic, ~95% hit-rate on DACH
   first names. Returns ``male`` / ``female`` / ``mostly_male`` / ``mostly_female``
   / ``andy`` / ``unknown``.
2. LLM bulk fallback — only the ``andy``/``unknown`` entries are forwarded to a
   single Anthropic call at the end of the linkedin stage. Implementation lives
   in ``app/leadgen/worker.py`` to keep this module dependency-free.

Confidence values are calibrated so the salutation logic in
``app/leadgen/contact_normalize.py`` can fall back to a neutral greeting when
``gender_confidence < 0.6``.
"""

from __future__ import annotations

import gender_guesser.detector as _gg

# A single Detector instance is thread-safe and reads its 50k-name table once.
_DETECTOR = _gg.Detector(case_sensitive=False)


# Library output → (gender, confidence)
# gender is normalised to "male" | "female" | None so the DB layer never sees
# the library's intermediate states.
_LIB_MAP: dict[str, tuple[str | None, float]] = {
    "male": ("male", 1.0),
    "female": ("female", 1.0),
    "mostly_male": ("male", 0.7),
    "mostly_female": ("female", 0.7),
    "andy": (None, 0.0),
    "unknown": (None, 0.0),
}


def guess_gender_from_first_name(
    first_name: str | None,
) -> tuple[str | None, float, str]:
    """Return ``(gender, confidence, method)`` for a single first name.

    ``method`` is one of ``library`` (deterministic library hit) or ``unknown``
    when the library could not classify. The caller decides whether to forward
    unknowns to the LLM.
    """
    if not first_name or not first_name.strip():
        return None, 0.0, "unknown"
    raw = _DETECTOR.get_gender(first_name.strip())
    gender, confidence = _LIB_MAP.get(raw, (None, 0.0))
    method = "library" if gender is not None else "unknown"
    return gender, confidence, method


def salutation_for(gender: str | None, confidence: float) -> str | None:
    """Return ``"Herr"`` / ``"Frau"`` or ``None`` when below confidence floor.

    ``None`` lets the templating layer fall back to a neutral greeting.
    """
    if gender is None or confidence < 0.6:
        return None
    if gender == "male":
        return "Herr"
    if gender == "female":
        return "Frau"
    return None
