"""Tests for the letter PDF renderer.

WeasyPrint is heavy and platform-dependent, so we keep most assertions
on the HTML-builder layer. One end-to-end test renders a real PDF and
checks the output is valid bytes that start with the PDF magic.
"""

from __future__ import annotations

import pytest

from app.letter.models import Letter, LetterTemplate
from app.letter.pdf_renderer import (
    PdfRendererError,
    _build_address_lines,
    _build_html,
    _resolve_letterhead_path,
    render_letter_pdf,
)

TENANT = "test-tenant"


def _make_template(
    *,
    letterhead_image_url: str | None = None,
    css_styles: str | None = None,
    header_html: str | None = None,
) -> LetterTemplate:
    return LetterTemplate(
        id=1,
        tenant_id=TENANT,
        name="Standard",
        format="a4",
        content_html="ignored",
        header_html=header_html,
        letterhead_image_url=letterhead_image_url,
        css_styles=css_styles,
        is_active=True,
    )


def _make_letter(
    *,
    name: str = "Max Mustermann",
    company: str | None = "ACME GmbH",
    street: str | None = "Musterstr. 1",
    zip_: str | None = "12345",
    city: str | None = "Musterstadt",
    country: str = "DE",
    body: str = "<p>Sehr geehrte Damen und Herren,</p><p>Test.</p>",
) -> Letter:
    return Letter(
        id=42,
        tenant_id=TENANT,
        template_id=1,
        recipient_name=name,
        recipient_company=company,
        recipient_street=street,
        recipient_zip=zip_,
        recipient_city=city,
        recipient_country=country,
        content_html=body,
        status="draft",
        send_mode="test",
    )


def test_address_lines_full():
    letter = _make_letter()
    lines = _build_address_lines(letter)
    assert lines == [
        "ACME GmbH",
        "Max Mustermann",
        "Musterstr. 1",
        "12345 Musterstadt",
    ]


def test_address_lines_skips_empty_and_appends_country_for_non_DE():
    letter = _make_letter(company=None, street=None, country="AT")
    lines = _build_address_lines(letter)
    assert lines == ["Max Mustermann", "12345 Musterstadt", "AT"]


def test_address_lines_returns_empty_when_nothing_set():
    letter = _make_letter(name="", company=None, street=None, zip_=None, city=None)
    assert _build_address_lines(letter) == []


def test_html_contains_address_in_din_5008_block():
    template = _make_template()
    letter = _make_letter()
    html = _build_html(letter, template, letterhead_path=None, extra_css=None)
    assert "ACME GmbH" in html
    assert "12345 Musterstadt" in html
    assert "address-block" in html
    assert "top: 50mm" in html  # DIN-5008 Form B address window
    assert "left: 25mm" in html


def test_html_includes_letterhead_when_path_resolves(tmp_path):
    fake_png = tmp_path / "letterhead.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n")
    template = _make_template(letterhead_image_url=str(fake_png))
    letter = _make_letter()
    html = _build_html(letter, template, letterhead_path=fake_png, extra_css=None)
    assert "background-image" in html
    assert fake_png.as_uri() in html


def test_html_uses_remote_url_directly_when_http():
    template = _make_template(
        letterhead_image_url="https://cdn.example.com/letterhead.png"
    )
    letter = _make_letter()
    # remote URLs return None from _resolve_letterhead_path, but _build_html still embeds them
    html = _build_html(letter, template, letterhead_path=None, extra_css=None)
    assert "https://cdn.example.com/letterhead.png" in html
    assert "background-image" in html


def test_html_includes_custom_css():
    template = _make_template(css_styles=".body { color: navy; }")
    letter = _make_letter()
    html = _build_html(letter, template, letterhead_path=None, extra_css=None)
    assert ".body { color: navy; }" in html


def test_html_escapes_html_in_recipient():
    letter = _make_letter(name="<script>x</script>", company="A&B GmbH")
    template = _make_template()
    html = _build_html(letter, template, letterhead_path=None, extra_css=None)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "A&amp;B" in html


def test_html_includes_sender_return_line_from_header_html():
    template = _make_template(header_html="ACME GmbH · Musterstr. 1 · 12345 Stadt")
    letter = _make_letter()
    html = _build_html(letter, template, letterhead_path=None, extra_css=None)
    assert "ACME GmbH · Musterstr. 1 · 12345 Stadt" in html
    assert "sender-return" in html


def test_resolve_letterhead_returns_none_for_blank():
    assert _resolve_letterhead_path(_make_template(), TENANT) is None


def test_resolve_letterhead_returns_none_for_remote_url():
    template = _make_template(letterhead_image_url="https://example.com/lh.png")
    assert _resolve_letterhead_path(template, TENANT) is None


def test_resolve_letterhead_finds_absolute_path(tmp_path):
    fake = tmp_path / "letterhead.png"
    fake.write_bytes(b"\x89PNG")
    template = _make_template(letterhead_image_url=str(fake))
    resolved = _resolve_letterhead_path(template, TENANT)
    assert resolved == fake


def test_render_rejects_missing_body():
    letter = _make_letter(body="")
    template = _make_template()
    with pytest.raises(PdfRendererError, match="content_html"):
        render_letter_pdf(letter, template, tenant_id=TENANT)


def test_render_rejects_missing_address():
    letter = _make_letter(name="", company=None, street=None, zip_=None, city=None)
    template = _make_template()
    with pytest.raises(PdfRendererError, match="Empfängeradresse"):
        render_letter_pdf(letter, template, tenant_id=TENANT)


def test_render_produces_valid_pdf_bytes():
    letter = _make_letter()
    template = _make_template()
    pdf = render_letter_pdf(letter, template, tenant_id=TENANT)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    # plausibly real (rough sanity, not exact)
    assert len(pdf) > 1000
