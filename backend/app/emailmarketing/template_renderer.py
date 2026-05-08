"""Email template rendering with merge-tag substitution.

Supports a richer tag syntax than the legacy ``replace_merge_tags`` in
``tracking.py``:

  - Simple tags: ``{{first_name}}``, ``{{tracking_hash}}``, ``{{unsubscribe_url}}``
  - Argument tags: ``{{tracking_link "/produkte"}}``

Click-tracking is done via the existing customer-journey infrastructure:
the rendered URL embeds a per-(contact, campaign) ``ref_code`` (6 chars)
plus UTM parameters. The customer-journey pixel on the landing site
resolves the ref_code → contact and writes the click event. There is no
email-side open pixel by design (DSGVO/TTDSG).

The ``ref_code`` is provided by the caller (``render_for_action`` does the
``RefCodeService.ensure_ref_code`` lookup before invoking this renderer).
If no ref_code is set, the link is built without ``?ref=`` — the page
visit is still trackable via UTM params, just not attributable to the
specific recipient.
"""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    from app.contacts.models import Contact
    from app.engagement.models import EngagementPipeline


TAG_PATTERN = re.compile(r'\{\{(\w+)(?:\s+"([^"]*)")?\}\}')


def render_tracking_link(
    path: str,
    pipeline: EngagementPipeline | None,
    *,
    ref_code: str | None = None,
) -> str:
    """Build a click-tracking URL with ``?ref={ref_code}`` + UTM params.

    Reads base URL + UTM defaults from ``pipeline.tracking_config`` if set;
    falls back to ``https://go4.energy`` and source=outreach.

    The ``ref_code`` is the 6-char ``JourneyRefCode.ref_code`` value for
    the current (contact, campaign) pair — NOT ``contact.tracking_hash``.
    The customer-journey pixel on go4.energy resolves the ref_code to the
    contact's tracking_hash and sets the cookie.
    """
    base = "https://go4.energy"
    utm: dict[str, str] = {}
    if pipeline is not None:
        cfg = getattr(pipeline, "tracking_config", None) or {}
        base = cfg.get("base_url") or base
        # Read both nested ({utm: {source, ...}}) and flat ({utm_source, ...})
        # shapes for backward compat. Only include UTM params that are
        # explicitly set — no fabricated defaults that surprise the user.
        utm_cfg = cfg.get("utm") or {}
        for short, long_ in (
            ("source", "utm_source"),
            ("medium", "utm_medium"),
            ("campaign", "utm_campaign"),
            ("term", "utm_term"),
            ("content", "utm_content"),
        ):
            value = utm_cfg.get(short) or cfg.get(long_) or ""
            if value:
                utm[long_] = value

    safe_path = path if path.startswith("/") else "/" + path

    params: dict[str, str] = {}
    if ref_code:
        params["ref"] = ref_code
    params.update(utm)

    if params:
        return f"{base.rstrip('/')}{safe_path}?{urlencode(params)}"
    return f"{base.rstrip('/')}{safe_path}"


def _split_name(full_name: str | None, part: str) -> str:
    """Best-effort split of full name into first / last."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if not parts:
        return ""
    if part == "first":
        return parts[0]
    if part == "last":
        return parts[-1] if len(parts) > 1 else ""
    return full_name


def _format_llm_body(text: str) -> str:
    """HTML-safe rendering of an LLM-generated plain-text body.

    Escapes HTML special chars (defense against prompt-injection), then
    converts paragraphs / newlines to <br> sequences so the body looks
    like the LLM intended without rendering raw markup.
    """
    if not text:
        return ""
    escaped = escape(text)
    # Two newlines = paragraph break, single newline = line break.
    paragraphs = escaped.split("\n\n")
    return "<br><br>".join(p.replace("\n", "<br>") for p in paragraphs)


def build_salutation_line(
    salutation: str | None, last_name: str | None
) -> str:
    """Baut die komplette Anrede-Zeile aus 'Herr'/'Frau' + Nachname.

    Fallback bei fehlenden Daten: ``Sehr geehrte Damen und Herren,``
    """
    sal = (salutation or "").strip().lower()
    last = (last_name or "").strip()
    if sal in ("herr", "mr") and last:
        return f"Sehr geehrter Herr {last},"
    if sal in ("frau", "ms", "mrs") and last:
        return f"Sehr geehrte Frau {last},"
    return "Sehr geehrte Damen und Herren,"


def render_template(
    html_content: str,
    *,
    contact: Contact,
    pipeline: EngagementPipeline | None = None,
    ref_code: str | None = None,
    llm_body: str | None = None,
    llm_subject: str | None = None,
    unsubscribe_url: str = "",
    impressum_block: str = "",
    extra_data: dict | None = None,
) -> str:
    """Substitute merge tags in HTML content.

    Unknown tags are left intact so a downstream pass (e.g. the legacy
    ``replace_merge_tags``) can fill them.

    ``ref_code`` is the 6-char Customer-Journey ref_code for this
    (contact, campaign) — used in ``{{tracking_link}}`` URLs. If None,
    links are built without ``?ref=``.
    """
    company_name = ""
    company_obj = getattr(contact, "company", None)
    if company_obj is not None:
        company_name = getattr(company_obj, "name", "") or ""
    if not company_name:
        company_name = getattr(contact, "company_name", "") or ""

    extra_data = extra_data or {}

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        arg = match.group(2)

        if name == "tracking_link":
            if not arg:
                return ""
            return render_tracking_link(arg, pipeline, ref_code=ref_code)
        if name == "ref_code":
            return ref_code or ""
        if name == "salutation_line":
            return extra_data.get(
                "salutation_line", "Sehr geehrte Damen und Herren,"
            )
        if name == "salutation":
            return extra_data.get("salutation", "Sehr geehrte Damen und Herren")
        if name == "contact_firstname":
            return extra_data.get("contact_firstname", "") or _split_name(
                contact.name, "first"
            )
        if name == "contact_lastname":
            return extra_data.get("contact_lastname", "") or _split_name(
                contact.name, "last"
            )
        if name == "contact_city":
            return extra_data.get("contact_city", "")
        if name == "contact_zip":
            return extra_data.get("contact_zip", "")
        if name == "tracking_hash":
            # Cookie-Hash der Person, NICHT der Kampagnen-Code. Selten
            # gebraucht — falls Templates es nutzen, liefern wir es weiter,
            # aber neue Templates sollen {{tracking_link}} verwenden.
            return contact.tracking_hash or ""
        if name == "llm_body":
            return _format_llm_body(llm_body or "")
        if name == "llm_subject":
            return escape(llm_subject or "")
        if name == "unsubscribe_url":
            return escape(unsubscribe_url) if unsubscribe_url else ""
        if name == "impressum_block":
            # Raw HTML by design — sourced from trusted tenant settings, not user input
            return impressum_block or ""
        if name == "disclaimer_block":
            # Raw HTML — generated from trusted tenant settings
            return extra_data.get("disclaimer_block", "")
        if name == "privacy_url":
            return escape(extra_data.get("privacy_url", "") or "")
        if name == "imprint_url":
            return escape(extra_data.get("imprint_url", "") or "")
        if name == "first_name":
            return _split_name(contact.name, "first")
        if name == "last_name":
            return _split_name(contact.name, "last")
        if name == "full_name":
            return contact.name or ""
        if name == "company_name":
            return company_name
        if name == "position":
            return getattr(contact, "position", "") or ""
        if name in extra_data:
            return str(extra_data[name])

        # Unknown — leave untouched so downstream renderers see it
        return match.group(0)

    return TAG_PATTERN.sub(_replace, html_content)


def extract_tags(content: str) -> list[tuple[str, str | None]]:
    """List all merge tags + arguments found in the content."""
    return [(m.group(1), m.group(2)) for m in TAG_PATTERN.finditer(content)]


def make_outreach_message_id(
    *,
    prefix: str,
    ref_id: int,
    token: str,
    domain: str = "smartladen.de",
) -> str:
    """Generate an RFC822 Message-ID header value for outreach matching.

    The poller reverse-looks-up replies by matching ``In-Reply-To`` /
    ``References`` headers against the value stored on the send record.

    Format: ``<{prefix}-{ref_id}-{token_short}@{domain}>``

    >>> make_outreach_message_id(prefix="rcpt", ref_id=42, token="abcdef123456")
    '<rcpt-42-abcdef12@smartladen.de>'
    """
    short = (token or "").replace("-", "")[:8]
    return f"<{prefix}-{ref_id}-{short}@{domain}>"
