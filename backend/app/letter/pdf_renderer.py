"""PDF rendering for letters.

Builds a DIN A4 portrait PDF with the recipient address positioned in
the DIN-5008 window so Letterxpress can extract it automatically. The
``LetterTemplate.letterhead_image_url`` is loaded as a CSS background
image, so the printed sheet looks like the tenant's pre-printed
letterhead. The body HTML and address fields come from the ``Letter``
record itself.

Layout follows DIN 5008 Form B (the modern standard):

    0–45 mm    : letterhead area (background image carries logo etc.)
    45–100 mm  : address window (recipient + sender return line)
    100–192 mm : body content
    250+ mm    : footer area (background image carries footer)

All coordinates are in millimetres because that's what the printer
cares about.
"""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from loguru import logger

from app.letter.models import Letter, LetterTemplate

# DIN 5008 Form B — modern standard letter format.
# https://de.wikipedia.org/wiki/DIN_5008
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297

ADDRESS_BLOCK_TOP_MM = 50
ADDRESS_BLOCK_LEFT_MM = 25
ADDRESS_BLOCK_WIDTH_MM = 85
ADDRESS_BLOCK_HEIGHT_MM = 40

SENDER_RETURN_TOP_MM = 45  # small "Absender" line just above address
BODY_TOP_MM = 100
BODY_LEFT_MM = 25
BODY_RIGHT_MARGIN_MM = 20

LETTERHEAD_DIR = Path("data/letter")  # base; tenant subdir resolved at runtime


class PdfRendererError(Exception):
    """Raised when WeasyPrint cannot build the PDF."""


def _resolve_letterhead_path(
    template: LetterTemplate,
    tenant_id: str,
) -> Path | None:
    """Resolve a template's letterhead URL/path to a filesystem path.

    Treats absolute URLs (http://, https://) as remote (we let WeasyPrint
    fetch them itself; a fallback handles missing ones). Relative values
    are interpreted as paths under ``data/letter/{tenant_id}/letterheads/``.
    """
    raw = (template.letterhead_image_url or "").strip()
    if not raw:
        return None
    if raw.startswith(("http://", "https://", "file://")):
        # WeasyPrint can fetch these directly; we just pass the URL through.
        return None
    candidate = Path(raw)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    rel = LETTERHEAD_DIR / tenant_id / "letterheads" / candidate.name
    if rel.exists():
        return rel.resolve()
    logger.warning(
        "Letterhead image not found: template={tid} url={url}",
        tid=template.id,
        url=raw,
    )
    return None


def _build_address_lines(letter: Letter) -> list[str]:
    """Recipient block, formatted for the DIN-5008 window.

    Letterxpress extracts the address from this block. Format:

        [Company]
        [Name]
        [Street]
        [Zip] [City]
        [Country if not DE]
    """
    lines: list[str] = []
    if letter.recipient_company:
        lines.append(letter.recipient_company)
    if letter.recipient_name:
        lines.append(letter.recipient_name)
    if letter.recipient_street:
        lines.append(letter.recipient_street)
    zip_city = " ".join(
        part for part in (letter.recipient_zip, letter.recipient_city) if part
    )
    if zip_city:
        lines.append(zip_city)
    if letter.recipient_country and letter.recipient_country.upper() != "DE":
        lines.append(letter.recipient_country.upper())
    return lines


def _sender_return_line(template: LetterTemplate) -> str | None:
    """Tiny 'Absender'-line above the recipient block.

    Pulled from a configured letterhead on the template (header_html
    field is repurposed: first line wins). Optional — return None if
    the template did not configure one.
    """
    if not template.header_html:
        return None
    first_line = template.header_html.strip().split("\n", 1)[0].strip()
    return first_line[:120] if first_line else None


def _build_html(
    letter: Letter,
    template: LetterTemplate,
    *,
    letterhead_path: Path | None,
    extra_css: str | None,
) -> str:
    """Assemble the full HTML document for WeasyPrint."""
    address_lines_html = "<br>".join(
        escape(line) for line in _build_address_lines(letter)
    )
    sender_return = _sender_return_line(template)
    sender_return_html = (
        f'<div class="sender-return">{escape(sender_return)}</div>'
        if sender_return
        else ""
    )

    if letterhead_path is not None:
        letterhead_uri = letterhead_path.as_uri()
        letterhead_css = (
            f'background-image: url("{letterhead_uri}"); '
            "background-size: 210mm 297mm; "
            "background-repeat: no-repeat; "
            "background-position: top left;"
        )
    elif template.letterhead_image_url and template.letterhead_image_url.startswith(
        ("http://", "https://")
    ):
        letterhead_css = (
            f'background-image: url("{template.letterhead_image_url}"); '
            "background-size: 210mm 297mm; "
            "background-repeat: no-repeat;"
        )
    else:
        letterhead_css = ""

    body_html = letter.content_html or ""
    today = datetime.now().strftime("%d.%m.%Y")
    custom_css = template.css_styles or ""
    extra_css_block = extra_css or ""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: 210mm 297mm;
    margin: 0;
}}
html, body {{
    margin: 0;
    padding: 0;
    width: 210mm;
    height: 297mm;
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 11pt;
    line-height: 1.45;
    color: #1a1a1a;
}}
.page {{
    position: relative;
    width: 210mm;
    height: 297mm;
    {letterhead_css}
}}
.address-block {{
    position: absolute;
    top: {ADDRESS_BLOCK_TOP_MM}mm;
    left: {ADDRESS_BLOCK_LEFT_MM}mm;
    width: {ADDRESS_BLOCK_WIDTH_MM}mm;
    height: {ADDRESS_BLOCK_HEIGHT_MM}mm;
    font-size: 10pt;
    line-height: 1.3;
}}
.sender-return {{
    position: absolute;
    top: {SENDER_RETURN_TOP_MM}mm;
    left: {ADDRESS_BLOCK_LEFT_MM}mm;
    width: {ADDRESS_BLOCK_WIDTH_MM}mm;
    font-size: 7pt;
    color: #555;
    border-bottom: 0.3pt solid #aaa;
    padding-bottom: 1mm;
    margin-bottom: 1mm;
}}
.body {{
    position: absolute;
    top: {BODY_TOP_MM}mm;
    left: {BODY_LEFT_MM}mm;
    right: {BODY_RIGHT_MARGIN_MM}mm;
    bottom: 30mm;
}}
.body p {{ margin: 0 0 4mm 0; }}
.date {{
    text-align: right;
    margin-bottom: 8mm;
    font-size: 10pt;
}}
{custom_css}
{extra_css_block}
</style>
</head>
<body>
<div class="page">
    {sender_return_html}
    <div class="address-block">{address_lines_html}</div>
    <div class="body">
        <div class="date">{escape(today)}</div>
        {body_html}
    </div>
</div>
</body>
</html>
"""


def render_letter_pdf(
    letter: Letter,
    template: LetterTemplate,
    *,
    tenant_id: str,
    extra_css: str | None = None,
) -> bytes:
    """Render a Letter into a DIN A4 PDF as bytes.

    The address block is positioned in the DIN-5008 window so the
    Letterxpress API can extract the recipient automatically. The
    template's ``letterhead_image_url`` is laid down as a full-page
    background so logo/footer/branding from the pre-existing
    letterhead carry through.
    """
    if not letter.content_html:
        raise PdfRendererError("Letter hat keinen content_html — nichts zu rendern.")
    lines = _build_address_lines(letter)
    if not lines:
        raise PdfRendererError(
            "Empfängeradresse fehlt komplett — Letterxpress kann das PDF "
            "nicht zuordnen."
        )
    # A deliverable address needs at minimum a street OR (zip + city).
    has_routing = bool(letter.recipient_street) or bool(
        letter.recipient_zip and letter.recipient_city
    )
    if not has_routing:
        raise PdfRendererError(
            "Empfängeradresse unvollständig — mindestens Straße oder "
            "PLZ + Ort sind nötig (DIN 5008)."
        )

    letterhead_path = _resolve_letterhead_path(template, tenant_id)
    html_str = _build_html(
        letter,
        template,
        letterhead_path=letterhead_path,
        extra_css=extra_css,
    )

    try:
        # Lazy import: WeasyPrint pulls in cairo/pango; only load when actually rendering.
        from weasyprint import HTML
    except (
        ImportError
    ) as exc:  # pragma: no cover — covered by environment, not unit tests
        raise PdfRendererError(
            "WeasyPrint nicht installiert. `pip install weasyprint` ausführen."
        ) from exc

    try:
        # base_url so relative <img> paths inside body_html resolve against tenant data dir
        tenant_base = (LETTERHEAD_DIR / tenant_id).resolve()
        base_url = tenant_base.as_uri() + "/" if tenant_base.exists() else None
        pdf_bytes = HTML(string=html_str, base_url=base_url).write_pdf()
    except Exception as exc:
        raise PdfRendererError(f"WeasyPrint-Fehler: {exc}") from exc

    if not pdf_bytes:
        raise PdfRendererError("WeasyPrint hat 0 Bytes zurückgegeben.")

    logger.info(
        "Rendered letter PDF: tenant={t} letter={lid} template={tid} bytes={n} letterhead={lh}",
        t=tenant_id,
        lid=letter.id,
        tid=template.id,
        n=len(pdf_bytes),
        lh=str(letterhead_path) if letterhead_path else "—",
    )
    return pdf_bytes
