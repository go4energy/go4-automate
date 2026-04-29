"""Aggregated contact context for the engagement brain.

Pulls together everything outreach-generators need to know about a
contact in a single dict-shaped payload, sourced from the central
``contacts`` / ``companies`` tables plus any module-extension data
the contact links to (currently leadgen via ``contacts.leadgen_place_id``).

This is the **read-side** counterpart to the principle that every
module extends ``contacts`` via FK rather than copying — the brain
calls ``get_contact_context(contact_id)`` and gets a flat snapshot
without needing to know which module provided which field.

Usage in the engagement brain::

    ctx = await get_contact_context(db, tenant_id, contact_id)
    prompt = LETTER_PROMPT.format(
        contact_name=ctx["name"],
        company=ctx["company_name"],
        personalization_hook=ctx.get("personalization_hook") or "",
        business_summary=ctx.get("business_summary") or "",
        primary_contact=ctx.get("primary_contact") or {},
        ...
    )
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Contact
from app.exceptions import NotFoundError


async def get_contact_context(
    db: AsyncSession,
    tenant_id: str,
    contact_id: int,
) -> dict[str, Any]:
    """Return a flattened context dict combining contact + company +
    leadgen-extension data (place, insights, impressum).

    Always returns a dict — leadgen fields are simply absent or ``None``
    when the contact has no leadgen origin. Callers should treat all
    leadgen-sourced keys as optional.
    """
    # Lazy import to avoid pulling leadgen models on import of contacts —
    # contacts is allowed to know about leadgen as a module-extension,
    # but we keep the dependency at runtime to prevent cycles.
    from app.leadgen.models import (
        LeadgenContact,
        LeadgenImpressum,
        LeadgenLLMInsights,
        LeadgenPlace,
    )

    contact_row = await db.execute(
        select(Contact)
        .options(selectinload(Contact.company))
        .where(Contact.id == contact_id, Contact.tenant_id == tenant_id)
    )
    contact = contact_row.scalar_one_or_none()
    if not contact:
        raise NotFoundError("Contact", contact_id)

    company = contact.company
    address = (company.address if company else None) or {}

    out: dict[str, Any] = {
        "contact_id": contact.id,
        "tenant_id": contact.tenant_id,
        "name": contact.name,
        "first_name": _first_token(contact.name),
        "last_name": _last_token(contact.name),
        "email": contact.email,
        "phone": contact.phone,
        "position": contact.position,
        "linkedin": contact.linkedin,
        "tags": list(contact.tags or []),
        "tracking_hash": contact.tracking_hash,
        "source": contact.source,
        # Company
        "company_id": company.id if company else None,
        "company_name": company.name if company else None,
        "company_website": company.website if company else None,
        "company_linkedin": company.linkedin_url if company else None,
        "address_street": address.get("street"),
        "address_zip": address.get("zip") or address.get("postal_code"),
        "address_city": address.get("city"),
        "address_country": address.get("country") or "DE",
        # Leadgen extension (filled in below if applicable)
        "leadgen_place_id": contact.leadgen_place_id,
        "leadgen_origin": contact.leadgen_place_id is not None,
        "personalization_hook": None,
        "target_match_score": None,
        "services": [],
        "brands": [],
        "customer_segments": [],
        "company_size_indicator": None,
        "red_flags": [],
        "primary_contact": None,
        "google_categories": [],
        "rating": None,
        "user_ratings_total": None,
        "leadgen_phone": None,  # impressum.phone — alternative if contact.phone missing
        "leadgen_email": None,  # impressum.email — alternative if contact.email synthetic
        "leadgen_managing_directors": [],
        "leadgen_handelsregister": None,
        "leadgen_linkedin_role": None,  # leadgen_contact.role
        "leadgen_gender": None,
    }

    if contact.leadgen_place_id is None:
        return out

    # Pull place + insights + impressum in one shot.
    place_row = await db.execute(
        select(LeadgenPlace).where(LeadgenPlace.id == contact.leadgen_place_id)
    )
    place = place_row.scalar_one_or_none()
    if place is None:
        # FK target was deleted (ON DELETE SET NULL kicks in eventually);
        # keep the contact-level data intact and bail.
        return out

    out["google_categories"] = list(place.google_categories or [])
    out["rating"] = float(place.rating) if place.rating is not None else None
    out["user_ratings_total"] = place.user_ratings_total
    # Backfill address from the place when company has none
    if not out["address_street"]:
        out["address_street"] = place.address_street
    if not out["address_zip"]:
        out["address_zip"] = place.address_zip
    if not out["address_city"]:
        out["address_city"] = place.address_city

    insights_row = await db.execute(
        select(LeadgenLLMInsights).where(LeadgenLLMInsights.place_id == place.id)
    )
    insights = insights_row.scalar_one_or_none()
    if insights is not None:
        out["personalization_hook"] = insights.personalization_hook
        out["target_match_score"] = insights.target_match_score
        out["services"] = list(insights.services or [])
        out["brands"] = list(insights.brands or [])
        out["customer_segments"] = list(insights.customer_segments or [])
        out["company_size_indicator"] = insights.company_size_indicator
        out["red_flags"] = list(insights.red_flags or [])
        out["primary_contact"] = insights.primary_contact

    impressum_row = await db.execute(
        select(LeadgenImpressum).where(LeadgenImpressum.place_id == place.id)
    )
    impressum = impressum_row.scalar_one_or_none()
    if impressum is not None:
        # Don't shadow contact-level fields, but expose them as alternatives.
        out["leadgen_phone"] = impressum.phone
        out["leadgen_email"] = impressum.email
        out["leadgen_managing_directors"] = list(impressum.managing_directors or [])
        out["leadgen_handelsregister"] = impressum.handelsregister

    # LinkedIn-side data lives on leadgen_contacts; pick the best matching one
    lc_row = await db.execute(
        select(LeadgenContact)
        .where(LeadgenContact.place_id == place.id)
        .order_by(LeadgenContact.id.asc())
        .limit(1)
    )
    leadgen_contact = lc_row.scalar_one_or_none()
    if leadgen_contact is not None:
        out["leadgen_linkedin_role"] = leadgen_contact.role
        out["leadgen_gender"] = leadgen_contact.gender

    return out


def _first_token(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().split(" ", 1)[0]


def _last_token(name: str | None) -> str:
    if not name:
        return ""
    parts = name.strip().split(" ")
    return parts[-1] if len(parts) > 1 else ""
