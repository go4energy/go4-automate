"""Impressum scraper for Stage 2 of the leadgen pipeline.

Fetches each Place's website, tries the common Impressum paths, extracts the
§5 TMG fields (managing directors, email, phone, postal address, HRB, USt-ID).
Kept pragmatic: regex + a bit of BeautifulSoup structural extraction, no LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; go4energy-leadgen/1.0)"

# Order matters: first hit wins. Most German sites use /impressum.
DEFAULT_PATHS: tuple[str, ...] = (
    "/impressum",
    "/impressum/",
    "/impressum.html",
    "/de/impressum",
    "/kontakt",
    "/kontakt/",
    "/legal/impressum",
)

# Single character class the charset filters share.
_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
)
# German phone: +49 or 0 + (area code) + digits, with optional separators.
_PHONE_RE = re.compile(
    r"(?:\+49|0)[\s\-/()]*\d(?:[\s\-/()]*\d){6,14}"
)
_HRB_RE = re.compile(r"\bHR[BA]\s*\d{3,8}\b", re.IGNORECASE)
_UST_ID_RE = re.compile(r"\bDE\s*\d{9}\b")
_MANAGER_LINE_RE = re.compile(
    r"(?:Geschäftsführer(?:in)?|Vertretungsberechtigt(?:er)?|Inhaber(?:in)?)"
    r"\s*:?\s*([^\n\r<]+)",
    re.IGNORECASE,
)
_PLZ_CITY_RE = re.compile(
    # PLZ + horizontal whitespace only + capital-led word chunk, stopping at
    # newline, colon, comma or two spaces so we don't swallow the next section.
    r"\b(\d{5})[ \t]+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]{1,60})(?=[\s]*(?:[\n\r:;,]|$))"
)


@dataclass
class ImpressumData:
    """Structured result of one Impressum scrape."""

    source_url: str | None = None
    email: str | None = None
    phone: str | None = None
    managing_directors: list[str] = field(default_factory=list)
    postal_address: str | None = None
    handelsregister: str | None = None
    ust_id: str | None = None
    raw_text_length: int = 0
    error: str | None = None


def _normalise_website(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    # Strip path/query/fragment - we want the origin for path composition.
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_manager_names(text: str) -> list[str]:
    names: list[str] = []
    for match in _MANAGER_LINE_RE.finditer(text):
        raw = match.group(1).strip(" :;,.")
        # Cut at sentence boundary or common field break.
        raw = re.split(r"\s{2,}|\n|;", raw, maxsplit=1)[0]
        # Filter out trivially invalid matches (e.g. empty, digits-only).
        if raw and len(raw) >= 3 and any(c.isalpha() for c in raw) and len(raw) <= 100:
            # Collapse multiple spaces.
            cleaned = re.sub(r"\s+", " ", raw).strip()
            if cleaned not in names:
                names.append(cleaned)
        if len(names) >= 5:
            break
    return names


def _extract_postal_address(text: str) -> str | None:
    m = _PLZ_CITY_RE.search(text)
    if not m:
        return None
    plz, city = m.group(1), m.group(2).strip()
    # Try to grab the street line preceding the PLZ line.
    prefix = text[: m.start()].rstrip()
    # Take the last non-empty line before PLZ as street.
    lines = [ln.strip() for ln in prefix.splitlines() if ln.strip()]
    street = lines[-1] if lines else ""
    # Sanity check street length.
    if len(street) > 120 or len(street) < 3:
        street = ""
    parts = [p for p in (street, f"{plz} {city}") if p]
    return ", ".join(parts) if parts else None


def parse_impressum_html(html: str, source_url: str) -> ImpressumData:
    """Pure function: take HTML, return extracted fields."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)

    emails = _EMAIL_RE.findall(text)
    email = _pick_first_business_email(emails)
    phones = _PHONE_RE.findall(text)
    phone = _clean_phone(phones[0]) if phones else None
    hrb = _match_first(_HRB_RE, text)
    ust = _match_first(_UST_ID_RE, text)
    if ust:
        ust = re.sub(r"\s+", "", ust)
    directors = _extract_manager_names(text)
    address = _extract_postal_address(text)

    return ImpressumData(
        source_url=source_url,
        email=email,
        phone=phone,
        managing_directors=directors,
        postal_address=address,
        handelsregister=hrb,
        ust_id=ust,
        raw_text_length=len(text),
    )


def _match_first(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    return m.group(0).strip() if m else None


def _pick_first_business_email(emails: list[str]) -> str | None:
    """Prefer business-looking emails over generic ones."""
    if not emails:
        return None
    # De-dupe while keeping order.
    seen: list[str] = []
    for e in emails:
        e = e.lower()
        if e not in seen:
            seen.append(e)
    # Rank: prefer info@, kontakt@, office@, then any non-noreply.
    preferred = ("info@", "kontakt@", "office@", "mail@", "hallo@")
    for pref in preferred:
        for e in seen:
            if e.startswith(pref) and "noreply" not in e and "no-reply" not in e:
                return e
    for e in seen:
        if "noreply" not in e and "no-reply" not in e:
            return e
    return seen[0]


def _clean_phone(raw: str) -> str:
    # Collapse to digits + leading + if present.
    plus = raw.strip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return raw.strip()
    if plus:
        return "+" + digits
    return digits


async def fetch_impressum(
    website: str,
    *,
    client: httpx.AsyncClient,
    paths: tuple[str, ...] = DEFAULT_PATHS,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout_s: float = 15.0,
) -> ImpressumData:
    """Try each candidate path until one returns a plausible Impressum."""
    origin = _normalise_website(website)
    if origin is None:
        return ImpressumData(error=f"Website ungültig: {website!r}")

    headers = {"User-Agent": user_agent, "Accept-Language": "de, en;q=0.5"}

    last_error: str | None = None
    for path in paths:
        url = urljoin(origin + "/", path.lstrip("/"))
        try:
            response = await client.get(
                url,
                headers=headers,
                timeout=timeout_s,
                follow_redirects=True,
            )
        except httpx.RequestError as e:
            last_error = f"{url}: {e.__class__.__name__}: {e}"
            continue

        if response.status_code != 200 or not response.text:
            last_error = f"{url}: HTTP {response.status_code}"
            continue

        data = parse_impressum_html(response.text, str(response.url))
        # If the candidate yielded at least email OR a phone, call it good.
        if data.email or data.phone or data.managing_directors:
            return data
        last_error = f"{url}: no contact fields extracted"

    return ImpressumData(error=last_error or "kein Impressum-Pfad gefunden")


__all__ = [
    "DEFAULT_PATHS",
    "DEFAULT_USER_AGENT",
    "ImpressumData",
    "fetch_impressum",
    "parse_impressum_html",
]
