"""Unit tests for email template renderer + Message-ID helper."""

from types import SimpleNamespace

from app.emailmarketing.template_renderer import (
    extract_tags,
    make_outreach_message_id,
    render_template,
    render_tracking_link,
)


def _contact(**overrides):
    base = {
        "name": "Max Mustermann",
        "tracking_hash": "abc123XYZ",
        "company": SimpleNamespace(name="Smartladen GmbH"),
        "company_name": None,
        "position": "CEO",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _pipeline(**overrides):
    base = {
        "slug": "lastmanagement-mfh",
        "tracking_config": {
            "base_url": "https://go4.energy",
            "utm": {
                "source": "outreach",
                "medium": "email",
                "campaign": "lastmanagement-mfh",
            },
        },
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ============== render_tracking_link ==============


def test_tracking_link_full_setup():
    url = render_tracking_link("/produkte", _contact(), _pipeline())
    assert url.startswith("https://go4.energy/produkte?")
    assert "ref=abc123XYZ" in url
    assert "utm_source=outreach" in url
    assert "utm_medium=email" in url
    assert "utm_campaign=lastmanagement-mfh" in url


def test_tracking_link_path_without_leading_slash_normalized():
    url = render_tracking_link("kontakt", _contact(), _pipeline())
    assert "go4.energy/kontakt?" in url


def test_tracking_link_no_pipeline_uses_defaults():
    url = render_tracking_link("/page", _contact(), None)
    assert url.startswith("https://go4.energy/page?")
    assert "ref=abc123XYZ" in url
    # no UTM params when pipeline absent
    assert "utm_source" not in url


def test_tracking_link_no_hash_omits_ref():
    contact = _contact(tracking_hash=None)
    url = render_tracking_link("/page", contact, _pipeline())
    assert "ref=" not in url
    assert "utm_source=outreach" in url


def test_tracking_link_custom_base_url():
    pipeline = _pipeline(tracking_config={"base_url": "https://smartladen.de"})
    url = render_tracking_link("/info", _contact(), pipeline)
    assert url.startswith("https://smartladen.de/info?")


# ============== render_template ==============


def test_template_substitutes_simple_tags():
    html = "Hallo {{first_name}}, von {{company_name}}!"
    out = render_template(html, contact=_contact(), pipeline=_pipeline())
    assert out == "Hallo Max, von Smartladen GmbH!"


def test_template_full_name_split():
    contact = SimpleNamespace(
        name="Anna Maria Beispiel",
        tracking_hash=None,
        company=None,
        company_name=None,
        position=None,
    )
    html = "[{{first_name}}|{{last_name}}|{{full_name}}]"
    out = render_template(html, contact=contact)
    assert out == "[Anna|Beispiel|Anna Maria Beispiel]"


def test_template_tracking_link_tag():
    html = '<a href=\'{{tracking_link "/produkte"}}\'>Mehr</a>'
    out = render_template(html, contact=_contact(), pipeline=_pipeline())
    assert "https://go4.energy/produkte?" in out
    assert "ref=abc123XYZ" in out


def test_template_tracking_hash_tag():
    out = render_template("HASH:{{tracking_hash}}", contact=_contact())
    assert out == "HASH:abc123XYZ"


def test_template_llm_body_html_escaped():
    """LLM output with HTML tags must be escaped to prevent injection."""
    html = "Body: {{llm_body}}"
    out = render_template(
        html,
        contact=_contact(),
        llm_body="<script>alert('x')</script>",
    )
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_template_llm_body_newlines_to_br():
    html = "Body: {{llm_body}}"
    out = render_template(
        html,
        contact=_contact(),
        llm_body="Hallo\nzwei Zeilen\n\nNeuer Absatz",
    )
    assert "Hallo<br>zwei Zeilen<br><br>Neuer Absatz" in out


def test_template_unsubscribe_url():
    out = render_template(
        '<a href="{{unsubscribe_url}}">Abmelden</a>',
        contact=_contact(),
        unsubscribe_url="https://api.go4.energy/t/u/abc",
    )
    assert "https://api.go4.energy/t/u/abc" in out


def test_template_impressum_block_raw_html():
    """Impressum is raw HTML by design (from trusted tenant settings)."""
    block = "<p><strong>Smartladen GmbH</strong><br>Musterstr. 1</p>"
    out = render_template(
        "{{impressum_block}}",
        contact=_contact(),
        impressum_block=block,
    )
    assert out == block


def test_template_unknown_tag_left_intact():
    out = render_template(
        "{{custom_thing}}",
        contact=_contact(),
    )
    assert out == "{{custom_thing}}"


def test_template_extra_data_overrides():
    out = render_template(
        "{{custom_thing}}",
        contact=_contact(),
        extra_data={"custom_thing": "Wert"},
    )
    assert out == "Wert"


def test_template_company_fallback_to_attribute():
    """When contact has no company relation, fall back to company_name attr."""
    contact = SimpleNamespace(
        name="Max",
        tracking_hash=None,
        company=None,
        company_name="DirectName GmbH",
        position=None,
    )
    out = render_template("{{company_name}}", contact=contact)
    assert out == "DirectName GmbH"


# ============== extract_tags ==============


def test_extract_tags_returns_name_and_arg():
    tags = extract_tags(
        'Hi {{first_name}}, see {{tracking_link "/x"}} and {{tracking_hash}}'
    )
    assert ("first_name", None) in tags
    assert ("tracking_link", "/x") in tags
    assert ("tracking_hash", None) in tags


# ============== make_outreach_message_id ==============


def test_message_id_format():
    mid = make_outreach_message_id(prefix="rcpt", ref_id=42, token="abcdef123456")
    assert mid == "<rcpt-42-abcdef12@smartladen.de>"


def test_message_id_strips_uuid_dashes():
    mid = make_outreach_message_id(
        prefix="rcpt",
        ref_id=7,
        token="abc-def-123456",
    )
    assert mid == "<rcpt-7-abcdef12@smartladen.de>"


def test_message_id_short_token_padding():
    mid = make_outreach_message_id(prefix="rcpt", ref_id=1, token="x")
    assert mid == "<rcpt-1-x@smartladen.de>"


def test_message_id_custom_domain():
    mid = make_outreach_message_id(
        prefix="seq",
        ref_id=99,
        token="00000000aaaa",
        domain="go4.energy",
    )
    assert mid == "<seq-99-00000000@go4.energy>"
