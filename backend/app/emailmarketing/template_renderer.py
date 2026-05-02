"""Email template rendering with merge-tag substitution.

Supports a richer tag syntax than the legacy ``replace_merge_tags`` in
``tracking.py``:

  - Simple tags: ``{{first_name}}``, ``{{tracking_hash}}``, ``{{unsubscribe_url}}``
  - Argument tags: ``{{tracking_link "/produkte"}}``

Click-tracking is done via the existing customer-journey infrastructure:
the rendered URL embeds ``contact.tracking_hash`` + UTM-parameters, and
the customer-journey pixel on the landing site records the click.
There is no email-side open pixel by design (DSGVO/TTDSG).
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
    contact: Contact,
    pipeline: EngagementPipeline | None,
) -> str:
    """Build a click-tracking URL with contact.tracking_hash + UTM params.

    Reads base URL + UTM defaults from ``pipeline.tracking_config`` if set;
    falls back to ``https://go4.energy`` and source=outreach.
    """
    base = "https://go4.energy"
    utm: dict[str, str] = {}
    if pipeline is not None:
        cfg = getattr(pipeline, "tracking_config", None) or {}
        base = cfg.get("base_url") or base
        utm_cfg = cfg.get("utm") or {}
        utm = {
            "utm_source": utm_cfg.get("source", "outreach"),
            "utm_medium": utm_cfg.get("medium", "email"),
            "utm_campaign": utm_cfg.get("campaign", pipeline.slug),
        }

    safe_path = path if path.startswith("/") else "/" + path

    params: dict[str, str] = {}
    if contact.tracking_hash:
        params["ref"] = contact.tracking_hash
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


def render_template(
    html_content: str,
    *,
    contact: Contact,
    pipeline: EngagementPipeline | None = None,
    llm_body: str | None = None,
    llm_subject: str | None = None,
    unsubscribe_url: str = "",
    impressum_block: str = "",
    extra_data: dict | None = None,
) -> str:
    """Substitute merge tags in HTML content.

    Unknown tags are left intact so a downstream pass (e.g. the legacy
    ``replace_merge_tags``) can fill them.
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
            return render_tracking_link(arg, contact, pipeline)
        if name == "tracking_hash":
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
