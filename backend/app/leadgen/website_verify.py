"""Verify whether a place really has no website by asking Google via Serper.

Google Places' ``websiteUri`` is only set when the business or Google itself
linked one. Many SMB / Praxis listings have a homepage that simply isn't in
Places. For homepage-sales campaigns we want to filter those out so they go
through the normal LLM analysis path rather than being scored as
"no homepage = top lead".

Approach: one Serper search per candidate, then a portal-blacklist + name-match
heuristic on the top organic results. If a non-portal domain matches the
business name, that is its homepage.

The blacklist is intentionally generic (directories, social platforms, search
engines) — campaign-specific extras come in via ``LLMStageConfig.serper_blacklist_extra``.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from loguru import logger

from app.utils.source_fetchers import fetch_websearch

# Hosts where a hit means "the practice is listed on a portal", NOT "this is
# their homepage". Anything matching here is excluded from the verify result.
DEFAULT_PORTAL_BLACKLIST: tuple[str, ...] = (
    # German doctor / business directories
    "jameda.de",
    "arzt-auskunft.de",
    "sanego.de",
    "doctolib.de",
    "doctolib.com",
    "samedi.de",
    "arzt-direkt.de",
    "arzttermine.de",
    "topmedic.de",
    "weisse-liste.de",
    "klinikbewertungen.de",
    "medfuehrer.de",
    # Generic German business directories
    "gelbeseiten.de",
    "11880.com",
    "dasoertliche.de",
    "das-oertliche.de",
    "branchenbuch.de",
    "yelp.de",
    "yelp.com",
    "firmenwissen.de",
    "stadtbranchenbuch.com",
    "stadtbranchenbuch.de",
    "openpr.de",
    "bewertet.de",
    # AT/CH directories
    "herold.at",
    "firmenabc.at",
    "wko.at",
    "local.ch",
    "search.ch",
    # Social / platforms
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "xing.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.de",
    "pinterest.com",
    # Google
    "google.com",
    "google.de",
    "maps.google.com",
    "maps.google.de",
    "business.site",
    "sites.google.com",
    # Wikipedia / news
    "wikipedia.org",
    "wikidata.org",
)


def _host_of(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h


def _is_blacklisted(host: str, extra: tuple[str, ...]) -> bool:
    if not host:
        return True
    for bad in DEFAULT_PORTAL_BLACKLIST + extra:
        bad = bad.lower().lstrip(".")
        if host == bad or host.endswith("." + bad):
            return True
    return False


_NAME_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]{3,}")
# Common business / address noise we strip before matching name tokens against
# the candidate domain — they don't carry identity.
_STOPWORDS = {
    "praxis", "dr", "drs", "dr.med", "drmed", "med", "medizin",
    "gmbh", "co", "kg", "ag", "ohg", "ug", "haftungsbeschraenkt",
    "the", "for", "und", "and", "von", "der", "die", "das",
    "fachaerzte", "facharzt", "zahnarzt", "zahnaerzte",
    "hausarzt", "hausaerzte", "kinderarzt",
    "gemeinschaftspraxis", "mvz",
}


def _normalize(s: str) -> str:
    s = s.lower()
    s = (
        s.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return s


def _name_tokens(name: str) -> set[str]:
    norm = _normalize(name or "")
    tokens = _NAME_TOKEN_RE.findall(norm)
    return {t for t in tokens if t not in _STOPWORDS and len(t) >= 3}


def _domain_root(host: str) -> str:
    """Return the second-level part of the domain for token-matching, e.g.
    ``praxis-mueller-berlin`` from ``www.praxis-mueller-berlin.de``."""
    parts = host.split(".")
    if len(parts) >= 2:
        return _normalize(parts[-2])
    return _normalize(host)


def _domain_matches_name(host: str, name_tokens: set[str]) -> bool:
    """At least one meaningful name token appears in the second-level domain."""
    if not name_tokens:
        return False
    root = _domain_root(host)
    if not root:
        return False
    return any(tok in root for tok in name_tokens)


def pick_homepage_from_results(
    results: list[dict],
    *,
    name: str,
    extra_blacklist: tuple[str, ...] = (),
    max_check: int = 5,
) -> str | None:
    """Return the first non-blacklisted URL in ``results`` whose domain
    plausibly matches ``name``. ``results`` are dicts with a ``url`` key,
    matching what fetch_websearch returns.
    """
    tokens = _name_tokens(name)
    for r in results[:max_check]:
        url = (r.get("url") or "").strip()
        if not url:
            continue
        host = _host_of(url)
        if _is_blacklisted(host, extra_blacklist):
            continue
        if not _domain_matches_name(host, tokens):
            continue
        return url
    return None


async def verify_no_website(
    *,
    name: str,
    city: str | None,
    serper_api_key: str,
    extra_blacklist: tuple[str, ...] = (),
) -> str | None:
    """One Serper query per place. Returns a URL if a plausible homepage was
    found, else None. Never raises — failures degrade to None and are logged.
    """
    if not serper_api_key:
        return None
    query_parts = [name.strip()]
    if city:
        query_parts.append(city.strip())
    query = " ".join(p for p in query_parts if p)[:200]
    if not query:
        return None
    try:
        results = await fetch_websearch([query], serper_api_key)
    except Exception as e:
        logger.debug("Serper verify_no_website failed for {n}: {e}", n=name, e=str(e))
        return None
    return pick_homepage_from_results(
        results, name=name, extra_blacklist=tuple(extra_blacklist or ())
    )


# Booking platforms / domain fragments that indicate the practice has an
# online appointment offer reachable from Google. Used by the calendar-flag
# heuristic during places-parse.
BOOKING_INDICATORS: tuple[str, ...] = (
    "doctolib.",
    "jameda.",
    "samedi.",
    "arzt-direkt.",
    "arzttermine.",
    "terminland.",
    "etermin.",
    "calendly.",
    "online-termin",
    "onlinetermin",
    "termin-buchen",
    "termin-online",
    "appointment",
    "reservewithgoogle",
    "reserve_with_google",
)


def detect_booking_link(payload: dict) -> bool:
    """Conservative heuristic on the Google Places raw payload: returns True
    if any field's string value contains a known booking-platform fragment.
    """
    if not isinstance(payload, dict):
        return False
    blob = _serialise(payload).lower()
    return any(needle in blob for needle in BOOKING_INDICATORS)


def _serialise(value, depth: int = 0) -> str:
    """Walk the payload and concatenate string values for substring search.
    Bounded depth so a pathological payload can't blow the stack."""
    if depth > 8:
        return ""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return ""
    if isinstance(value, list):
        return " ".join(_serialise(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return " ".join(_serialise(v, depth + 1) for v in value.values())
    return ""


__all__ = [
    "BOOKING_INDICATORS",
    "DEFAULT_PORTAL_BLACKLIST",
    "detect_booking_link",
    "pick_homepage_from_results",
    "verify_no_website",
]
