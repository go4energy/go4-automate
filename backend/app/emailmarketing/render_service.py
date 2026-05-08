"""Render service — single source of truth for outbound email HTML.

Used both at send-time (worker) and for previews (UI). Takes the
pieces (template, contact, brain-output) and produces the final
subject + HTML body ready for the provider.
"""

from __future__ import annotations

import json
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.customer_journey.service import CampaignService, RefCodeService
from app.emailmarketing.models import EmailTemplate
from app.emailmarketing.template_renderer import build_salutation_line, render_template
from app.engagement.models import EngagementPipeline, PendingAction, PipelineEnrollment
from app.exceptions import NotFoundError
from app.tenant_settings.service import (
    TenantMasterDataService,
    build_disclaimer_block,
    build_impressum_block,
)


async def _load_primary_contact_extras(
    db: AsyncSession, contact_id: int
) -> dict:
    """Holt aus ``leadgen_llm_insights.primary_contact`` die Anrede-Daten
    sowie aus ``leadgen_places`` die Stadt/PLZ des Empfängers.

    Liefert die Keys ``salutation``, ``contact_firstname``,
    ``contact_lastname``, ``salutation_line``, ``contact_city``,
    ``contact_zip`` — alle optional, leer wenn keine Insights verfügbar.
    """
    try:
        from app.leadgen.models import LeadgenLLMInsights, LeadgenPlace
    except ImportError:
        return {}

    # Place + Insights in einem Query — die Stadt brauchen wir auch wenn
    # primary_contact nicht befüllt ist (z.B. Firmen ohne benannten GF).
    row = (
        await db.execute(
            select(
                LeadgenLLMInsights.primary_contact,
                LeadgenPlace.address_city,
                LeadgenPlace.address_zip,
            )
            .outerjoin(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            )
            .where(LeadgenPlace.contact_id == contact_id)
            .limit(1)
        )
    ).first()

    primary, city, zip_code = (None, "", "") if row is None else row
    primary = primary if isinstance(primary, dict) else None

    sal = (primary.get("salutation") or "").strip() if primary else ""
    first = (primary.get("first_name") or "").strip() if primary else ""
    last = (primary.get("last_name") or "").strip() if primary else ""

    return {
        "salutation": (
            "Sehr geehrter Herr"
            if sal.lower() == "herr"
            else "Sehr geehrte Frau"
            if sal.lower() == "frau"
            else "Sehr geehrte Damen und Herren"
        ),
        "contact_firstname": first,
        "contact_lastname": last,
        "salutation_line": build_salutation_line(sal, last),
        "contact_city": (city or "").strip(),
        "contact_zip": (zip_code or "").strip(),
    }


def _build_unsubscribe_url(
    contact: Contact, custom_base: str | None = None
) -> str:
    """Build absolute opt-out URL — must be reachable from any mail client.

    Reihenfolge:
    1. ``custom_base`` (aus Tenant-Stammdaten ``unsubscribe_url_base``) —
       z.B. ``https://smartladen.de/abmelden/`` für Brand-Konsistenz
    2. Fallback ``settings.app_url + /api/v1/emailmarketing/t/u/``

    Email-Clients können KEINE relativen URLs auflösen (sie kennen unseren
    Host nicht), daher muss die URL absolut sein.
    """
    if not contact.tracking_hash:
        return ""
    if custom_base:
        # Custom-Base muss auf "/" enden — Tracking-Hash wird angehängt
        base = custom_base.rstrip("/") + "/"
        return f"{base}{contact.tracking_hash}"
    from app.config import settings
    base = (settings.app_url or "https://automate.go4.energy").rstrip("/")
    return f"{base}/api/v1/emailmarketing/t/u/{contact.tracking_hash}"


async def _load_tenant_compliance(
    db: AsyncSession, tenant_id: str
) -> dict:
    """Lädt Impressum-Block + DSGVO-Disclaimer + URLs aus tenant_master_data.

    Liefert leere Strings wenn der Tenant noch keine Stammdaten gepflegt
    hat — Renderer kommt dann ohne Footer durch, das Email zeigt aber
    deutlich dass etwas fehlt (gewollt, damit man's bemerkt und nachpflegt).
    """
    row = await TenantMasterDataService(db).get(tenant_id)
    return {
        "impressum_block": build_impressum_block(row),
        "disclaimer_block": build_disclaimer_block(row),
        "privacy_url": (row.privacy_url if row else None) or "",
        "imprint_url": (row.imprint_url if row else None) or "",
        "unsubscribe_url_base": (
            row.unsubscribe_url_base if row else None
        ) or "",
    }


def _parse_personalized(payload: Any) -> dict:
    """Accept either a dict (already parsed JSONB) or a JSON-encoded string."""
    if isinstance(payload, dict):
        return payload
    if not payload:
        return {}
    try:
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


async def _load_contact(db: AsyncSession, contact_id: int) -> Contact:
    contact = (
        await db.execute(
            select(Contact)
            .options(selectinload(Contact.company))
            .where(Contact.id == contact_id)
        )
    ).scalar_one_or_none()
    if not contact:
        raise NotFoundError("Contact", contact_id)
    # Tracking-Hash ist Voraussetzung für Unsubscribe-Link + ggf. Cookie-
    # Identifikation. Wenn Cold-Outreach an einen importierten Contact
    # geht, der noch nie auf der Webseite war, fehlt der Hash → wir
    # generieren ihn beim ersten Render und persistieren.
    if not contact.tracking_hash:
        from app.contacts.utils import generate_tracking_hash
        contact.tracking_hash = generate_tracking_hash()
        await db.flush()
    return contact


async def _load_template(db: AsyncSession, template_id: int) -> EmailTemplate:
    tpl = (
        await db.execute(
            select(EmailTemplate).where(EmailTemplate.id == template_id)
        )
    ).scalar_one_or_none()
    if not tpl:
        raise NotFoundError("EmailTemplate", template_id)
    return tpl


def _resolve_template_id(action: PendingAction, pipeline: EngagementPipeline) -> int | None:
    """Pick the template to use for a given pending_action.

    Lookup order:
      1. action.context.template_id (explicit override)
      2. pipeline.tracking_config.email_template_id (per-pipeline default)
      3. None — caller falls back to a minimal text-only render
    """
    ctx = action.context or {}
    if ctx.get("template_id"):
        return int(ctx["template_id"])
    tc = pipeline.tracking_config or {}
    if tc.get("email_template_id"):
        return int(tc["email_template_id"])
    return None


def _minimal_html_fallback(personalized: dict, contact: Contact) -> str:
    """When no template is configured for the pipeline, render a stripped
    plain-text-ish HTML so the user can still preview / send.

    Layout: greeting + LLM body + simple sign-off. Plain enough to look
    like a personal mail, structured enough to host the merge tags."""
    body = personalized.get("llm_body", "")
    name = (contact.name or "").strip()
    salutation = "Sehr geehrte/r " + (name or "Damen und Herren")
    return (
        '<div style="font-family:Arial,sans-serif;font-size:14px;line-height:1.55;color:#222">'
        f"<p>{escape(salutation)},</p>"
        f"<p>{escape(body).replace(chr(10), '<br>')}</p>"
        '<p>Mit freundlichen Grüßen,<br>go4.energy GmbH</p>'
        '<p style="margin-top:24px;font-size:11px;color:#888">'
        '{{unsubscribe_url}} • {{impressum_block}}'
        '</p></div>'
    )


async def _ensure_journey_ref_code(
    db: AsyncSession,
    action: PendingAction,
    pipeline: EngagementPipeline,
    contact: Contact,
) -> str | None:
    """Idempotent: hole oder erzeuge den Customer-Journey-Ref-Code für
    (Contact, Pipeline-Campaign). Cached die Ref-Code-ID auf dem Enrollment.

    Returns the 6-char ``ref_code`` string, or None if anything went wrong.
    A failed lookup must NOT break the render — links fall back to no
    ``?ref=`` (UTM-only attribution).
    """
    try:
        campaign = await CampaignService(db).ensure_for_pipeline(pipeline)

        utm_cfg = (pipeline.tracking_config or {}).get("utm") or {}
        target_url = (pipeline.tracking_config or {}).get("base_url")
        ref = await RefCodeService(db).ensure_ref_code(
            tenant_id=pipeline.tenant_id,
            contact=contact,
            campaign=campaign,
            target_url=target_url,
            utm_source=utm_cfg.get("source", "outreach"),
            utm_medium=utm_cfg.get("medium", "email"),
            utm_campaign=utm_cfg.get("campaign", pipeline.slug),
        )

        # Cache pointer on enrollment so subsequent renders skip the lookup
        if action.enrollment_id:
            enrollment = (
                await db.execute(
                    select(PipelineEnrollment).where(
                        PipelineEnrollment.id == action.enrollment_id
                    )
                )
            ).scalar_one_or_none()
            if enrollment is not None and enrollment.journey_ref_code_id != ref.id:
                enrollment.journey_ref_code_id = ref.id
                await db.flush()
        return ref.ref_code
    except Exception:
        # Don't let tracking-link prep break the actual mail render.
        from loguru import logger
        logger.exception(
            "ensure_ref_code failed for action {aid}; rendering without ref",
            aid=action.id,
        )
        return None


async def render_for_action(
    db: AsyncSession,
    action: PendingAction,
    tenant_config: dict | None = None,
) -> dict:
    """Render the full email for a given pending_action.

    Returns ``{"subject": str, "html": str, "text": str, "template_id": int|None,
    "personalized": dict, "ref_code": str|None}``.
    """
    pipeline = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == action.pipeline_id
            )
        )
    ).scalar_one_or_none()
    if not pipeline:
        raise NotFoundError("Pipeline", action.pipeline_id)

    contact = await _load_contact(db, action.contact_id)
    personalized = _parse_personalized(action.suggested_content)
    template_id = _resolve_template_id(action, pipeline)

    # Single source of truth: ensure the Customer-Journey ref_code exists
    # for this (contact, pipeline-campaign). Idempotent — bulk-pregenerated
    # codes are reused, JIT codes are created here.
    ref_code = await _ensure_journey_ref_code(db, action, pipeline, contact)

    # Primary-Contact-Daten aus den Lead-Insights (falls vorhanden) als
    # extra_data — damit Templates {{salutation_line}}, {{contact_lastname}}
    # etc. korrekt füllen statt aus dem Firmennamen abzuleiten.
    extra_data = await _load_primary_contact_extras(db, contact.id)

    # Compliance-Block aus tenant_master_data (Impressum + Disclaimer + URLs)
    compliance = await _load_tenant_compliance(db, pipeline.tenant_id)
    extra_data.update(
        {
            "disclaimer_block": compliance["disclaimer_block"],
            "privacy_url": compliance["privacy_url"],
            "imprint_url": compliance["imprint_url"],
        }
    )

    if template_id:
        tpl = await _load_template(db, template_id)
        html = tpl.html_content
        text = tpl.text_content or ""
        # Subject: prefer the LLM-generated subject; fall back to template subject.
        raw_subject = personalized.get("llm_subject") or tpl.subject
    else:
        html = _minimal_html_fallback(personalized, contact)
        text = personalized.get("llm_body", "")
        raw_subject = personalized.get("llm_subject", "(kein Betreff)")

    rendered_html = render_template(
        html,
        contact=contact,
        pipeline=pipeline,
        ref_code=ref_code,
        llm_body=personalized.get("llm_body"),
        llm_subject=personalized.get("llm_subject"),
        unsubscribe_url=_build_unsubscribe_url(
            contact, custom_base=compliance.get("unsubscribe_url_base")
        ),
        impressum_block=compliance["impressum_block"],
        extra_data=extra_data,
    )
    rendered_subject = render_template(
        raw_subject or "",
        contact=contact,
        pipeline=pipeline,
        ref_code=ref_code,
        llm_body=personalized.get("llm_body"),
        llm_subject=personalized.get("llm_subject"),
        extra_data=extra_data,
    )

    return {
        "subject": rendered_subject.strip(),
        "html": rendered_html,
        "text": text,
        "template_id": template_id,
        "personalized": personalized,
        "ref_code": ref_code,
        "contact_email": contact.email,
        "contact_name": contact.name,
    }
