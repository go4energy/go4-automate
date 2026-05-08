"""Helpers for turning legacy leadgen name data into ``leadgen_contacts`` rows.

Both ``LeadgenImpressum.managing_directors`` (list[str]) and
``LeadgenLLMInsights.primary_contact`` (JSONB) need to be normalised into the
new schema. The functions here are pure (no DB access) so they can be unit-
tested against the fixtures in ``backend/tests/fixtures/legacy_names.json``.
"""

from __future__ import annotations

# Common honorifics / titles to strip before splitting first/last name.
_TITLE_TOKENS = {
    "dr.",
    "dr",
    "prof.",
    "prof",
    "dipl.",
    "dipl",
    "ing.",
    "ing",
    "mag.",
    "mag",
    "med.",
    "med",
    "med.dr",
    "phd",
    "msc",
    "ba",
    "ma",
    "mba",
    "herr",
    "frau",
}


def split_name(raw: str) -> tuple[str, str]:
    """Split a ``"Vorname Nachname"`` (or longer) string into (first, last).

    Strategy:
    - strip leading academic titles (``Dr.``, ``Prof.``, …)
    - first whitespace-token = first name, the rest = last name
    - returns ``("", "")`` when the input is unusable
    """
    if not raw:
        return "", ""
    tokens = [t.strip() for t in raw.strip().split() if t.strip()]
    while tokens and tokens[0].lower().rstrip(".") in _TITLE_TOKENS:
        tokens.pop(0)
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return tokens[0], ""
    return tokens[0], " ".join(tokens[1:])


def normalize_full_name(raw: str) -> str:
    """Lowercase, collapse whitespace — used for the unique-key on rows."""
    return " ".join((raw or "").strip().split()).strip()


def from_managing_director_string(name: str) -> dict | None:
    """Build a dict suitable for ``LeadgenContact`` insertion from a raw name.

    Returns ``None`` when the input does not yield at least a first name. The
    title-stripped form is used for ``full_name`` so the per-place uniqueness
    constraint deduplicates "Dr. Max Mustermann" and "Max Mustermann".
    """
    cleaned = normalize_full_name(name)
    if not cleaned:
        return None
    first, last = split_name(cleaned)
    if not first:
        return None
    canonical = f"{first} {last}".strip() if last else first
    return {
        "first_name": first or None,
        "last_name": last or None,
        "full_name": canonical,
        "role": "Geschäftsführer",
        "source": "managing_director",
    }


def from_primary_contact_dict(blob: dict | None) -> dict | None:
    """Build a dict from the legacy ``LLMInsights.primary_contact`` JSONB.

    Honours the ``gender`` / ``salutation`` fields the LLM has historically
    written so we don't pay for re-classification on backfilled rows.
    """
    if not isinstance(blob, dict):
        return None
    first = (blob.get("first_name") or "").strip()
    last = (blob.get("last_name") or "").strip()
    if not first and not last:
        return None
    full = (f"{first} {last}".strip()) or None
    if not full:
        return None
    raw_gender = (blob.get("gender") or "").strip().lower()
    gender: str | None = None
    if raw_gender in ("m", "male"):
        gender = "male"
    elif raw_gender in ("f", "female"):
        gender = "female"
    elif (blob.get("salutation") or "").strip().lower() == "herr":
        gender = "male"
    elif (blob.get("salutation") or "").strip().lower() == "frau":
        gender = "female"
    return {
        "first_name": first or None,
        "last_name": last or None,
        "full_name": full,
        "role": blob.get("role") or "Geschäftsführer",
        "source": "primary_contact",
        # Gender came from a previous LLM run — high confidence.
        "gender": gender,
        "gender_confidence": 1.0 if gender else 0.0,
        "gender_method": "jsonb_legacy" if gender else None,
    }
