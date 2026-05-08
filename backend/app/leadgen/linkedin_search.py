"""Serper-backed LinkedIn URL discovery for the linkedin worker stage.

Two helpers, each one Serper call:

- ``find_company_linkedin_url(name, city, ...)`` → /company/<slug> URL (or None)
- ``find_person_linkedin_url(first_name, last_name, company, city, ...)`` →
  /in/<slug> URL (or None)

Both functions degrade silently to ``None`` on quota / network errors so the
worker stage cannot crash a run. The returned tuple includes a confidence
score (0..1) that the caller writes into ``leadgen_contacts.linkedin_match_confidence``
so the UI can flag low-confidence guesses.

Cost reference: Serper charges ~$0.30 per 1000 queries on the Production plan,
so a 100-place campaign with Ø 2 GFs spends 100 + 200 = 300 queries ≈ $0.09.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from loguru import logger

from app.utils.source_fetchers import fetch_websearch

_PERSON_HOST_RE = re.compile(r"linkedin\.com/in/", re.IGNORECASE)
_COMPANY_HOST_RE = re.compile(r"linkedin\.com/(company|school)/", re.IGNORECASE)

# Confidence floor for accepting a Serper hit. Set after the first 100-place
# pilot showed too many false positives at 0.5 (e.g. ua.linkedin.com hits and
# /in/ slugs that were actually company profiles).
ACCEPT_THRESHOLD = 0.6

# Only DACH + global LinkedIn locales are valid hits — rejects ua/ru/cn etc.
_ALLOWED_HOSTS: frozenset[str] = frozenset(
    {"www.linkedin.com", "de.linkedin.com", "at.linkedin.com", "ch.linkedin.com"}
)

# Slug fragments that mark a /in/ URL as actually a company profile (LinkedIn
# allows custom vanity slugs that contain Rechtsformen). Reject those for
# person matching.
_FIRM_SLUG_TOKENS: tuple[str, ...] = ("gmbh", "ohg", "kg", "ag", "gbr", "ug", "se")


def _slug_of(url: str) -> str:
    """Return the LinkedIn slug after ``/in/`` or ``/company/``, lowercase."""
    try:
        path = urlparse(url).path or ""
    except ValueError:
        return ""
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0].lower() in ("in", "company", "school"):
        return parts[1].lower()
    return ""


def _has_firm_slug(url: str) -> bool:
    """Detect ``/in/<slug>`` URLs whose slug is actually a company name."""
    slug = _slug_of(url)
    if not slug:
        return False
    return any(f"-{tok}" in slug or slug.endswith(f"-{tok}") for tok in _FIRM_SLUG_TOKENS)


def _normalise(url: str) -> str:
    url = url.strip()
    for sep in ("?", "#"):
        if sep in url:
            url = url.split(sep, 1)[0]
    return url.rstrip("/")


def _is_linkedin_host(url: str) -> bool:
    """Strict host check — only DACH + global LinkedIn locales count.

    Rejects e.g. ``ua.linkedin.com`` which surfaced as a top hit during the
    pilot run for "Elektro Häcker GmbH" and pointed to a completely different
    company. Localised LinkedIn pages aren't useful for German B2B outreach.
    """
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in _ALLOWED_HOSTS


def _score_person_match(
    title: str,
    snippet: str,
    *,
    first_name: str,
    last_name: str,
    company: str | None,
) -> float:
    """Heuristic 0..1 score: name + (optional) company keywords in title/snippet."""
    blob = f"{title} {snippet}".lower()
    score = 0.0
    if first_name and first_name.lower() in blob:
        score += 0.4
    if last_name and last_name.lower() in blob:
        score += 0.4
    if company:
        # Cheap brand match: any token >= 4 chars from the company name.
        tokens = [
            t.lower()
            for t in re.split(r"[\s,.&\-/]+", company)
            if len(t) >= 4
        ]
        for t in tokens:
            if t in blob:
                score += 0.2
                break
    return min(score, 1.0)


def _score_company_match(title: str, snippet: str, *, name: str) -> float:
    blob = f"{title} {snippet}".lower()
    score = 0.0
    tokens = [t.lower() for t in re.split(r"[\s,.&\-/]+", name) if len(t) >= 4]
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in blob)
    score = hits / len(tokens)
    return min(score, 1.0)


async def find_company_linkedin_url(
    *,
    name: str,
    city: str | None,
    serper_api_key: str,
) -> tuple[str | None, float]:
    """Return ``(url, confidence)`` for the most plausible /company/ URL."""
    if not serper_api_key or not name:
        return None, 0.0
    parts = [name.strip()]
    if city:
        parts.append(city.strip())
    query = "site:linkedin.com/company " + " ".join(p for p in parts if p)
    query = query[:200]
    try:
        results = await fetch_websearch([query], serper_api_key)
    except Exception as e:  # noqa: BLE001
        logger.debug("Serper company-linkedin failed: {e}", e=str(e))
        return None, 0.0
    best_url: str | None = None
    best_score = 0.0
    for r in results:
        url = (r.get("url") or "").strip()
        if not url or not _is_linkedin_host(url):
            continue
        if not _COMPANY_HOST_RE.search(url):
            continue
        s = _score_company_match(r.get("title") or "", r.get("summary") or "", name=name)
        if s > best_score:
            best_score = s
            best_url = _normalise(url)
    # Apply the global accept threshold so callers can rely on a binary
    # "URL or None" decision without each having to enforce the floor.
    if best_score < ACCEPT_THRESHOLD:
        return None, best_score
    return best_url, best_score


async def find_person_linkedin_url(
    *,
    first_name: str,
    last_name: str,
    company: str | None,
    city: str | None,
    serper_api_key: str,
) -> tuple[str | None, float]:
    """Return ``(url, confidence)`` for the most plausible /in/ URL."""
    if not serper_api_key or not (first_name or last_name):
        return None, 0.0
    full = f'"{first_name} {last_name}"'.strip()
    if not full or full == '""':
        return None, 0.0
    parts = ["site:linkedin.com/in", full]
    if company:
        parts.append(f'"{company}"')
    if city:
        parts.append(city.strip())
    query = " ".join(parts)[:200]
    try:
        results = await fetch_websearch([query], serper_api_key)
    except Exception as e:  # noqa: BLE001
        logger.debug("Serper person-linkedin failed: {e}", e=str(e))
        return None, 0.0
    best_url: str | None = None
    best_score = 0.0
    for r in results:
        url = (r.get("url") or "").strip()
        if not url or not _is_linkedin_host(url):
            continue
        if not _PERSON_HOST_RE.search(url):
            continue
        # Reject /in/ URLs whose slug is actually a company name. These
        # surfaced during the pilot run e.g. "/in/eab-elektro-anlagen-bau-gmbh".
        if _has_firm_slug(url):
            continue
        s = _score_person_match(
            r.get("title") or "",
            r.get("summary") or "",
            first_name=first_name,
            last_name=last_name,
            company=company,
        )
        if s > best_score:
            best_score = s
            best_url = _normalise(url)
    if best_score < ACCEPT_THRESHOLD:
        return None, best_score
    return best_url, best_score
