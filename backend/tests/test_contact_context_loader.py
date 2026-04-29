"""Tests for app.contacts.context_loader.get_contact_context.

The loader is the read-side of the "extend contacts via FK, never copy"
principle. We verify both branches: bare contacts (no leadgen origin)
and contacts with a linked leadgen_place + insights + impressum.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.context_loader import get_contact_context
from app.contacts.models import Company, Contact
from app.exceptions import NotFoundError
from app.leadgen.models import (
    LeadgenCampaign,
    LeadgenImpressum,
    LeadgenLLMInsights,
    LeadgenPlace,
)

TENANT = "test-tenant"


async def _seed_bare_contact(db: AsyncSession) -> Contact:
    company = Company(
        tenant_id=TENANT,
        name="ACME GmbH",
        address={"street": "Musterstr. 1", "zip": "12345", "city": "Stadt"},
    )
    db.add(company)
    await db.flush()

    contact = Contact(
        tenant_id=TENANT,
        name="Max Mustermann",
        email="max@acme.example",
        phone="+49 30 12345",
        position="Geschäftsführer",
        company_id=company.id,
        tags=["leadgen"],
    )
    db.add(contact)
    await db.flush()
    return contact


async def _seed_leadgen_origin(db: AsyncSession, contact: Contact) -> LeadgenPlace:
    campaign = LeadgenCampaign(
        tenant_id=TENANT, name="Campaign", slug="cmp", status="ready",
    )
    db.add(campaign)
    await db.flush()

    place = LeadgenPlace(
        tenant_id=TENANT,
        campaign_id=campaign.id,
        google_place_id="ChIJ1234",
        name="ACME GmbH",
        address_street="Musterstr. 1",
        address_zip="12345",
        address_city="Stadt",
        google_categories=["electrician", "service"],
        rating=4.7,
        user_ratings_total=42,
        contact_id=contact.id,
    )
    db.add(place)
    await db.flush()

    contact.leadgen_place_id = place.id

    insights = LeadgenLLMInsights(
        tenant_id=TENANT,
        place_id=place.id,
        target_match_score=8,
        services=["E-Mobility", "Wallboxen"],
        brands=["Hager", "ABB"],
        customer_segments=["Gewerbe", "Industrie"],
        company_size_indicator="GmbH mit 5-10 Mitarbeitern",
        personalization_hook="Wallbox-Kompetenz mit Gewerbe-Fokus",
        red_flags=[],
        primary_contact={"first_name": "Max", "last_name": "Mustermann", "role": "GF"},
    )
    db.add(insights)

    impressum = LeadgenImpressum(
        tenant_id=TENANT,
        place_id=place.id,
        email="info@acme.example",
        phone="+49 30 99999",
        managing_directors=[{"name": "Max Mustermann"}],
        handelsregister="HRB 12345",
    )
    db.add(impressum)
    await db.flush()
    return place


# ============== Tests ==============


@pytest.mark.asyncio
async def test_bare_contact_returns_basic_fields(db_session: AsyncSession):
    contact = await _seed_bare_contact(db_session)

    ctx = await get_contact_context(db_session, TENANT, contact.id)

    assert ctx["contact_id"] == contact.id
    assert ctx["name"] == "Max Mustermann"
    assert ctx["first_name"] == "Max"
    assert ctx["last_name"] == "Mustermann"
    assert ctx["email"] == "max@acme.example"
    assert ctx["company_name"] == "ACME GmbH"
    assert ctx["address_zip"] == "12345"
    assert ctx["leadgen_origin"] is False
    # Insights default empty
    assert ctx["personalization_hook"] is None
    assert ctx["services"] == []


@pytest.mark.asyncio
async def test_leadgen_origin_pulls_insights(db_session: AsyncSession):
    contact = await _seed_bare_contact(db_session)
    place = await _seed_leadgen_origin(db_session, contact)

    ctx = await get_contact_context(db_session, TENANT, contact.id)

    assert ctx["leadgen_origin"] is True
    assert ctx["leadgen_place_id"] == place.id
    assert ctx["personalization_hook"] == "Wallbox-Kompetenz mit Gewerbe-Fokus"
    assert ctx["target_match_score"] == 8
    assert "E-Mobility" in ctx["services"]
    assert "Hager" in ctx["brands"]
    assert "Gewerbe" in ctx["customer_segments"]
    assert ctx["company_size_indicator"].startswith("GmbH")
    assert ctx["google_categories"] == ["electrician", "service"]
    assert ctx["rating"] == 4.7
    assert ctx["user_ratings_total"] == 42
    assert ctx["leadgen_phone"] == "+49 30 99999"
    assert ctx["leadgen_email"] == "info@acme.example"
    assert ctx["leadgen_handelsregister"] == "HRB 12345"
    assert ctx["primary_contact"]["last_name"] == "Mustermann"


@pytest.mark.asyncio
async def test_address_falls_back_to_place_when_company_has_none(
    db_session: AsyncSession,
):
    company = Company(tenant_id=TENANT, name="No-Address GmbH")  # no address dict
    db_session.add(company)
    await db_session.flush()

    contact = Contact(
        tenant_id=TENANT,
        name="X Y",
        email="x@y.example",
        company_id=company.id,
    )
    db_session.add(contact)
    await db_session.flush()

    campaign = LeadgenCampaign(tenant_id=TENANT, name="C", slug="c", status="ready")
    db_session.add(campaign)
    await db_session.flush()

    place = LeadgenPlace(
        tenant_id=TENANT,
        campaign_id=campaign.id,
        google_place_id="ChIJxx",
        name="No-Address",
        address_street="Hauptstr. 5",
        address_zip="98765",
        address_city="Andernort",
    )
    db_session.add(place)
    await db_session.flush()
    contact.leadgen_place_id = place.id
    await db_session.flush()

    ctx = await get_contact_context(db_session, TENANT, contact.id)
    assert ctx["address_street"] == "Hauptstr. 5"
    assert ctx["address_zip"] == "98765"
    assert ctx["address_city"] == "Andernort"


@pytest.mark.asyncio
async def test_unknown_contact_raises(db_session: AsyncSession):
    with pytest.raises(NotFoundError):
        await get_contact_context(db_session, TENANT, 999_999)


@pytest.mark.asyncio
async def test_orphan_leadgen_place_id_does_not_crash(db_session: AsyncSession):
    """If the leadgen_place_id points to a place that no longer exists
    (e.g. deleted concurrently), we degrade gracefully — return the
    contact-level data without insights."""
    contact = await _seed_bare_contact(db_session)
    contact.leadgen_place_id = 12_345_678  # nonexistent
    await db_session.flush()

    ctx = await get_contact_context(db_session, TENANT, contact.id)
    assert ctx["leadgen_origin"] is True  # the FK is set
    assert ctx["personalization_hook"] is None  # but the data is missing
    assert ctx["services"] == []
