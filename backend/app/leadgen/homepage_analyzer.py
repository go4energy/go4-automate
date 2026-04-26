"""Homepage analyzer for Stage 3 of the leadgen pipeline.

Fetches a handful of pages from a Place's website, strips HTML to plain text,
then asks Claude to score relevance against the campaign's target_profile and
extract marketing-relevant insights (services, brands, customer segments,
company size indicators, personalization hook).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

DEFAULT_PATHS: tuple[str, ...] = (
    "/",
    "/impressum",
    "/impressum/",
    "/ueber-uns",
    "/ueber-uns/",
    "/about",
    "/leistungen",
    "/services",
    "/kontakt",
)


DEFAULT_PROMPT_TEMPLATE = """Du analysierst die Website eines Unternehmens im Auftrag eines B2B-Akquise-Teams.

DEINE AUFGABE: Material für ein nachgelagertes Mail-/Brief-Modul sammeln, das spaeter eine
personalisierte Erstansprache formuliert. Du formulierst die Ansprache NICHT — du sammelst
strukturiertes Intel.

ZIELPROFIL (so sieht ein idealer Lead aus):
{target_profile}

WAS DAS NACHGELAGERTE MODUL BRAUCHT:
{output_description}

Analysiere den folgenden Website-Inhalt und gib AUSSCHLIESSLICH ein JSON-Objekt mit genau diesen Feldern zurück:
{{
  "target_match_score": 0-10,
  "services": ["max 5 konkrete Dienstleistungen die die Firma anbietet"],
  "brands": ["erwaehnte Hersteller/Marken"],
  "customer_segments": ["WEG", "Hausverwaltung", "Gewerbe", "Industrie", "EFH", "Kommune", ...],
  "company_size_indicator": "1 Satz zur Firmengroesse / Mitarbeiterzahl falls erkennbar (max 200 Zeichen)",
  "personalization_hook": "PRE-PITCH-INTEL als Stichpunkte (3-5 Bullets) — KEINE Anrede, KEIN Pitch. Nur Beobachtungen und Brueckenpunkte fuer das spaetere Mail-Modul. Format: '- ...\\n- ...\\n- ...' max 800 Zeichen.",
  "red_flags": ["Konkrete Negativ-Indikatoren, max 3. WICHTIG: 'Eigenes Energiemanagement-/Lastmanagement-System bereits vorhanden' = harter Treffer. Ebenso: Whitelabel-Software-Anbieter im EMS-Bereich, reiner EFH-Markt, 1-Mann-Betrieb."],
  "primary_contact": {{
    "salutation": "Herr|Frau|null wenn unklar",
    "first_name": "Vorname (Doppelnamen mit Bindestrich erhalten)",
    "last_name": "Nachname",
    "gender": "m|f|null wenn unklar",
    "role": "Geschaeftsfuehrer|Inhaber|Vertrieb|Ansprechpartner E-Mobility|... (so wie auf der Website genannt)",
    "source": "team-seite|kontakt-seite|impressum|unklar"
  }},
  "impressum": {{
    "email": "Hauptkontakt-Email aus Impressum oder leer",
    "phone": "Telefon aus Impressum oder leer",
    "managing_directors": ["NUR echte Personennamen wie 'Max Mustermann'. NIEMALS 'Herr', 'Frau', 'Geschaeftsfuehrer' allein, keine Bruchstuecke."],
    "postal_address": "Strasse Hausnr, PLZ Ort - oder leer",
    "handelsregister": "z.B. 'HRB 12345 Amtsgericht Berlin' oder leer",
    "ust_id": "z.B. 'DE123456789' oder leer"
  }}
}}

SCORING (target_match_score 0-10):
- 0-3: passt nicht (z.B. eigenes EMS, reiner EFH-Markt, kein Bezug zum Zielprofil)
- 4-6: koennte passen, aber unklare Signale
- 7-8: gute Passung, mehrere SOLL-Kriterien erfuellt
- 9-10: ideal, alle MUSS-Kriterien erfuellt + klare SOLL-Indikatoren

REGEL primary_contact: Bevorzuge operative Vertriebs-/E-Mobility-Person aus Team- oder
Kontakt-Seite. Fallback: erste/r Geschaeftsfuehrer/in aus Impressum. Bei mehreren GFs:
den/die mit sichtbarem Vertriebs-/Wallbox-Bezug. Wenn kein klarer Kontakt findbar:
alle Felder null — NICHT raten.

REGEL personalization_hook: Stichpunkte mit echten, konkreten Beobachtungen vom Webauftritt
(Projekte, Spezialisierungen, sichtbare Luecken). KEINE Floskeln wie "etabliertes
Unternehmen". KEINE Anrede, KEIN Pitch — das macht ein anderes Modul.

REGEL impressum.managing_directors: Lieber leer als raten. Nur klare Vor+Nachname-Kombis
aus Impressum-Sektionen.

WEBSITE-INHALT:
{content}
"""


@dataclass
class LLMAnalysis:
    """Structured LLM verdict for one place."""

    target_match_score: int | None = None
    services: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)
    customer_segments: list[str] = field(default_factory=list)
    company_size_indicator: str | None = None
    personalization_hook: str | None = None
    red_flags: list[str] = field(default_factory=list)
    primary_contact: dict | None = None
    impressum_fallback: dict = field(default_factory=dict)
    pages_analyzed: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: int = 0
    model_used: str | None = None
    error: str | None = None


def _normalise_website(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    # Collapse runs of whitespace lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


async def fetch_pages(
    website: str,
    *,
    client: httpx.AsyncClient,
    paths: tuple[str, ...] = DEFAULT_PATHS,
    user_agent: str,
    timeout_s: float,
    max_pages: int = 5,
) -> dict[str, str]:
    """Fetch a small set of pages; return dict of final_url -> plain text."""
    origin = _normalise_website(website)
    if not origin:
        return {}

    headers = {"User-Agent": user_agent, "Accept-Language": "de, en;q=0.5"}
    out: dict[str, str] = {}
    for path in paths:
        if len(out) >= max_pages:
            break
        url = urljoin(origin + "/", path.lstrip("/"))
        if url in out:
            continue
        try:
            resp = await client.get(
                url, headers=headers, timeout=timeout_s, follow_redirects=True
            )
        except httpx.RequestError as e:
            logger.debug("homepage fetch {u}: {e}", u=url, e=str(e))
            continue
        if resp.status_code != 200 or not resp.text:
            continue
        text = _extract_text(resp.text)
        if len(text) < 50:
            continue
        out[str(resp.url)] = text
    return out


def build_combined_content(pages: dict[str, str], max_chars: int) -> str:
    """Combine page texts with URL headers; truncate to max_chars (budget-safe)."""
    parts: list[str] = []
    remaining = max_chars
    for url, text in pages.items():
        header = f"--- {url} ---\n"
        # Reserve some budget for the header itself.
        budget = max(0, remaining - len(header))
        if budget < 200:
            break
        snippet = text[:budget]
        parts.append(header + snippet)
        remaining -= len(header) + len(snippet)
        if remaining < 500:
            break
    return "\n\n".join(parts)


def target_profile_hash(target_profile: str, prompt_template: str, model: str) -> str:
    """Stable hash so we can detect when a re-run is needed."""
    payload = f"{model}\n{prompt_template}\n{target_profile}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _parse_llm_json(raw: str) -> dict:
    """Strip ```json fences, parse."""
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def _normalise_analysis(payload: dict) -> dict:
    """Whitelist + coerce LLM output, keep it defensive."""
    # Accept both new key (target_match_score) and legacy (pv_relevance_score) so
    # transitional LLM outputs still parse.
    score = payload.get("target_match_score")
    if score is None:
        score = payload.get("pv_relevance_score")
    try:
        score = int(score) if score is not None else None
        if score is not None:
            score = max(0, min(10, score))
    except (TypeError, ValueError):
        score = None

    def _as_list(v, max_items=10):
        if not isinstance(v, list):
            return []
        return [str(x)[:200] for x in v[:max_items] if x]

    # Accept both old key 'impressum_fallback' and new 'impressum' for flexibility
    impressum_data = payload.get("impressum") or payload.get("impressum_fallback") or {}
    if not isinstance(impressum_data, dict):
        impressum_data = {}

    return {
        "target_match_score": score,
        "services": _as_list(payload.get("services"), 10),
        "brands": _as_list(payload.get("brands"), 10),
        "customer_segments": _as_list(payload.get("customer_segments"), 10),
        "company_size_indicator": (
            # DB column is String(200); cap there to avoid truncation errors.
            str(payload.get("company_size_indicator"))[:200]
            if payload.get("company_size_indicator")
            else None
        ),
        "personalization_hook": (
            str(payload.get("personalization_hook"))[:2000]
            if payload.get("personalization_hook")
            else None
        ),
        "red_flags": _as_list(payload.get("red_flags"), 5),
        "primary_contact": _clean_primary_contact(payload.get("primary_contact")),
        "impressum_fallback": _clean_impressum_payload(impressum_data),
    }


def _clean_primary_contact(value) -> dict | None:
    """Whitelist the primary_contact subobject; return None if no useful info."""
    if not isinstance(value, dict):
        return None

    def _str(field_name: str, max_len: int = 100) -> str | None:
        v = value.get(field_name)
        if v is None:
            return None
        s = str(v).strip()
        if not s or s.lower() in {"null", "none", "unklar", "n/a"}:
            return None
        return s[:max_len]

    salutation = _str("salutation", 10)
    if salutation and salutation.lower() not in {"herr", "frau"}:
        salutation = None
    gender = _str("gender", 5)
    if gender and gender.lower() not in {"m", "f"}:
        gender = None
    cleaned = {
        "salutation": salutation,
        "first_name": _str("first_name", 80),
        "last_name": _str("last_name", 80),
        "gender": gender.lower() if gender else None,
        "role": _str("role", 200),
        "source": _str("source", 50),
    }
    # If everything is None, drop the contact entirely.
    if not any(v for v in cleaned.values()):
        return None
    return cleaned


_BAD_DIRECTOR_TOKENS = {
    "herr", "frau", "geschäftsführer", "geschäftsführerin",
    "vertretungsberechtigt", "vertretungsberechtigter",
    "inhaber", "inhaberin", "geschaeftsfuehrer", "geschaeftsfuehrerin",
}


def _is_real_person_name(name: str) -> bool:
    """Heuristic: must have 2+ tokens with capital letters, not a generic label."""
    name = (name or "").strip()
    if len(name) < 4 or len(name) > 100:
        return False
    if name.lower() in _BAD_DIRECTOR_TOKENS:
        return False
    # Reject single-word "Herr" / "Frau" / "Geschäftsführer"
    tokens = name.split()
    if len(tokens) < 2:
        return False
    # Reject if the whole thing is essentially one of the bad tokens with a
    # trailing fragment ("Herr Max" is fine; "Herr" alone is not).
    return any(len(tok) >= 2 and tok[0].isupper() for tok in tokens)


_PROSE_NEGATIVES = (
    "nicht ", "kein", "leer", "missing", "not found",
    "auf der website", "auf website", "im inhalt", "im auszug",
    "im bereitgestellten", "siehe ", "tba", "n/a", "keine angabe",
)


def _looks_like_prose_negative(value: str) -> bool:
    """Detect LLM 'nicht gefunden'-style prose in fields meant to be values."""
    v = (value or "").strip().lower()
    if not v:
        return True
    if len(v) > 200:
        return True
    return any(neg in v for neg in _PROSE_NEGATIVES)


def _accept_email(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    if "@" not in v or _looks_like_prose_negative(v):
        return None
    return v[:320]


def _accept_phone(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    if _looks_like_prose_negative(v):
        return None
    # Must contain at least 5 digits to be plausible.
    if sum(c.isdigit() for c in v) < 5:
        return None
    return v[:50]


def _accept_short(value: str | None, max_len: int) -> str | None:
    if not value:
        return None
    v = str(value).strip()
    if _looks_like_prose_negative(v):
        return None
    return v[:max_len]


def _clean_impressum_payload(d: dict) -> dict:
    """Trim/sanitise the impressum block coming from the LLM."""
    out: dict = {}
    if (email := _accept_email(d.get("email"))):
        out["email"] = email
    if (phone := _accept_phone(d.get("phone"))):
        out["phone"] = phone
    if (addr := _accept_short(d.get("postal_address"), 500)):
        out["postal_address"] = addr
    if (hr := _accept_short(d.get("handelsregister"), 100)):
        out["handelsregister"] = hr
    if (ust := _accept_short(d.get("ust_id"), 50)):
        out["ust_id"] = ust
    raw_directors = d.get("managing_directors") or []
    if isinstance(raw_directors, list):
        cleaned = [str(x).strip() for x in raw_directors if x]
        cleaned = [n for n in cleaned if _is_real_person_name(n)]
        out["managing_directors"] = cleaned[:5]
    return out


# Per-million-token pricing in USD-cents, sourced from Anthropic price list.
# Cache-read tokens are 10% of base input; cache-write is 125% of base input.
# Ollama / local models cost 0 (electricity tracked separately if at all).
_PRICING_CENTS_PER_M: dict[str, dict[str, int]] = {
    "claude-haiku-4-5": {"input": 100, "output": 500},
    "claude-sonnet-4-6": {"input": 300, "output": 1500},
    "claude-opus-4-7": {"input": 1500, "output": 7500},
}
_DEFAULT_PRICING = {"input": 100, "output": 500}


def _is_local_model(model: str) -> bool:
    """Local Ollama models all carry the ``ollama:``/``qwen``/``llama``/``mistral``
    prefix and have no per-token API price."""
    m = (model or "").lower()
    return (
        m.startswith("qwen")
        or m.startswith("llama")
        or m.startswith("mistral")
        or m.startswith("gemma")
        or m.startswith("phi")
        or m.startswith("ollama:")
    )


def _estimate_cost_cents(
    input_tokens: int,
    output_tokens: int,
    *,
    model: str = "claude-haiku-4-5",
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> int:
    """Compute USD-cents cost from the reported token usage.

    ``input_tokens`` is already exclusive of cached reads in the SDK response,
    so we just add the discounted contribution from cache_read separately.
    Local Ollama models always cost 0.
    """
    if _is_local_model(model):
        return 0
    p = _PRICING_CENTS_PER_M.get(model, _DEFAULT_PRICING)
    base_input = p["input"]
    output = p["output"]
    cache_read = max(1, base_input // 10)  # 10% of input price
    cache_create = int(base_input * 1.25)  # 125% of input price
    cents = (
        input_tokens * base_input
        + output_tokens * output
        + cache_read_tokens * cache_read
        + cache_creation_tokens * cache_create
    ) / 1_000_000
    return max(0, int(round(cents)))


async def analyze_place_with_llm(
    *,
    website: str,
    target_profile: str,
    output_description: str = "",
    prompt_template: str,
    model: str,
    provider: str = "anthropic",
    llm_service,
    http_client: httpx.AsyncClient,
    paths: tuple[str, ...],
    user_agent: str,
    timeout_s: float,
    max_html_chars: int,
) -> LLMAnalysis:
    """Full pipeline for one place: fetch pages, LLM call, parse."""
    pages = await fetch_pages(
        website,
        client=http_client,
        paths=paths,
        user_agent=user_agent,
        timeout_s=timeout_s,
    )
    if not pages:
        return LLMAnalysis(
            error="Homepage nicht erreichbar oder leer",
            model_used=model,
        )

    content = build_combined_content(pages, max_html_chars)
    od = output_description.strip() or "(keine zusätzlichen Wünsche)"
    # Format defensively: a user-supplied template may not have
    # {output_description}; .format_map with defaultdict gracefully ignores it.
    from collections import defaultdict
    fmt_args: dict[str, str] = defaultdict(str)
    fmt_args["target_profile"] = target_profile.strip()
    fmt_args["output_description"] = od
    fmt_args["content"] = content
    user_prompt = prompt_template.format_map(fmt_args)
    system_prompt = (
        "Du bist ein sorgfältiger B2B-Analyst. Antworte ausschließlich mit "
        "gültigem JSON - kein Fließtext, keine Erklärung drumherum."
    )

    # Auto-detect provider when model name implies it (saves a config step).
    effective_provider = "ollama" if _is_local_model(model) else (provider or "anthropic")

    try:
        raw, usage = await llm_service.generate_with_usage(
            provider=effective_provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            # Opus produces longer JSON than Haiku; bumped to avoid mid-response
            # truncation when the LLM lists many services / projects / brands.
            max_tokens=4096,
        )
    except Exception as e:
        return LLMAnalysis(
            error=f"LLM-Fehler: {e.__class__.__name__}: {e}",
            pages_analyzed=list(pages.keys()),
            model_used=model,
        )

    try:
        payload = _parse_llm_json(raw)
    except Exception as e:
        return LLMAnalysis(
            error=f"JSON parse fail: {e}",
            pages_analyzed=list(pages.keys()),
            model_used=model,
        )

    fields = _normalise_analysis(payload)

    # Real token usage straight from the Anthropic response, with provider-
    # specific pricing applied. Falls back to a char-count estimate if the
    # provider didn't return usage (e.g. Ollama).
    input_tokens = int(usage.get("input_tokens") or max(1, len(user_prompt) // 4))
    output_tokens = int(usage.get("output_tokens") or max(1, len(raw) // 4))
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    cache_create = int(usage.get("cache_creation_input_tokens") or 0)
    cost = _estimate_cost_cents(
        input_tokens,
        output_tokens,
        model=model,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_create,
    )

    return LLMAnalysis(
        target_match_score=fields["target_match_score"],
        services=fields["services"],
        brands=fields["brands"],
        customer_segments=fields["customer_segments"],
        company_size_indicator=fields["company_size_indicator"],
        personalization_hook=fields["personalization_hook"],
        red_flags=fields["red_flags"],
        primary_contact=fields["primary_contact"],
        impressum_fallback=fields["impressum_fallback"],
        pages_analyzed=list(pages.keys()),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_cents=cost,
        model_used=model,
    )


__all__ = [
    "DEFAULT_PATHS",
    "DEFAULT_PROMPT_TEMPLATE",
    "LLMAnalysis",
    "analyze_place_with_llm",
    "build_combined_content",
    "fetch_pages",
    "target_profile_hash",
]
