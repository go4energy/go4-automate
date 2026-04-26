"""Demo workspace seeding for new tenants.

When a fresh tenant is created (Managed Service onboarding, SaaS sign-up,
agency white-label provisioning) it lands on a blank workspace and the
user has nothing to click on. This module fills that void with a
representative-but-removable sample dataset:

- 1 default sales pipeline with 5 stages
- 5 sample companies across different industries
- 15 sample contacts (~3 per company)
- 5 sample deals scattered across stages
- 3 reusable email templates

Goals:
- Idempotent: running it twice on the same tenant is a no-op (detected
  via the demo-tag on companies).
- Removable: every demo entity carries a 'demo' tag so the UI can offer
  a "demo data wegräumen" button later.
- NOT auto-invoked: Sprint-0 ships the function only. Wiring it into
  Tenant-creation happens after we validated against go4.energy.

Usage:
    from app.setup.demo_seed import seed_demo_workspace
    await seed_demo_workspace(db, tenant_id="some-tenant")
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.models import Company, Contact
from app.crm.models import CrmDeal, CrmPipeline, CrmPipelineStage
from app.emailmarketing.models import EmailTemplate

DEMO_TAG = "demo"


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------

_COMPANIES = [
    {
        "name": "Sonne & Strom GmbH",
        "domain": "sonne-strom.de",
        "industry": "Energie",
        "size": "10-50",
        "description": "Regionaler Solar-Installateur, Schwerpunkt PV + Wallbox.",
    },
    {
        "name": "Müller Elektrotechnik",
        "domain": "mueller-elektro.de",
        "industry": "Handwerk",
        "size": "5-10",
        "description": "Klassischer Elektrofachbetrieb, neu im E-Mobility-Geschäft.",
    },
    {
        "name": "Praxis Dr. Schmidt",
        "domain": "praxis-schmidt.de",
        "industry": "Gesundheitswesen",
        "size": "1-5",
        "description": "Hausarztpraxis mit veralteter Homepage.",
    },
    {
        "name": "Werner Hausverwaltung",
        "domain": "werner-immo.de",
        "industry": "Immobilien",
        "size": "10-50",
        "description": "Hausverwaltung für Wohnungen, sucht WEG-Ladelösungen.",
    },
    {
        "name": "BackHaus Bäckerei",
        "domain": "backhaus-baeckerei.de",
        "industry": "Lebensmittel",
        "size": "10-50",
        "description": "Familienbetrieb, möchte digitalen Auftritt erneuern.",
    },
]

# 3 contacts per company on average → 15 total
_CONTACTS_BY_COMPANY = {
    "Sonne & Strom GmbH": [
        ("Anna", "Berger", "anna.berger@sonne-strom.de", "Geschäftsführerin"),
        ("Tobias", "Hoffmann", "t.hoffmann@sonne-strom.de", "Vertriebsleiter"),
        ("Kira", "Lindner", "k.lindner@sonne-strom.de", "Service-Leitung"),
    ],
    "Müller Elektrotechnik": [
        ("Klaus", "Müller", "k.mueller@mueller-elektro.de", "Inhaber"),
        ("Steffen", "Bauer", "s.bauer@mueller-elektro.de", "Vorarbeiter"),
        ("Janine", "Krüger", "j.krueger@mueller-elektro.de", "Büro"),
    ],
    "Praxis Dr. Schmidt": [
        ("Markus", "Schmidt", "info@praxis-schmidt.de", "Praxisinhaber"),
        ("Susanne", "Weber", "s.weber@praxis-schmidt.de", "Praxismanagerin"),
        ("Dr. Lisa", "Köhler", "l.koehler@praxis-schmidt.de", "Ärztin"),
    ],
    "Werner Hausverwaltung": [
        ("Werner", "Schulze", "w.schulze@werner-immo.de", "Geschäftsführer"),
        ("Maria", "Beck", "m.beck@werner-immo.de", "Objektleiterin"),
        ("Frederik", "Rossi", "f.rossi@werner-immo.de", "Buchhaltung"),
    ],
    "BackHaus Bäckerei": [
        ("Helmut", "Kraus", "h.kraus@backhaus-baeckerei.de", "Inhaber"),
        ("Petra", "Kraus", "p.kraus@backhaus-baeckerei.de", "Backstube"),
        ("Lukas", "Vogel", "l.vogel@backhaus-baeckerei.de", "Filiale Mitte"),
    ],
}

_PIPELINE_STAGES = [
    ("Erstkontakt",   0, 10,  "#94A3B8", False, False),
    ("Qualifiziert",  1, 30,  "#60A5FA", False, False),
    ("Angebot",       2, 60,  "#FBBF24", False, False),
    ("Verhandlung",   3, 80,  "#A78BFA", False, False),
    ("Gewonnen",      4, 100, "#34D399", True,  False),
    ("Verloren",      5, 0,   "#F87171", False, True),
]

# Each tuple: (deal-title, company-name, stage-name, value-eur, days-until-close)
_DEALS = [
    ("Komplettpaket Marketing-Automation", "Sonne & Strom GmbH",     "Angebot",      19_900, 21),
    ("Homepage + Lead-Generierung",        "Müller Elektrotechnik",  "Qualifiziert",  4_900, 14),
    ("Neue Praxis-Homepage",               "Praxis Dr. Schmidt",     "Erstkontakt",   2_490,  7),
    ("WEG-Ladestrom Software-Integration", "Werner Hausverwaltung",  "Verhandlung",  29_500, 30),
    ("Digital-Auftritt Bäckerei",          "BackHaus Bäckerei",      "Gewonnen",      3_600,   0),
]

_EMAIL_TEMPLATES = [
    {
        "name": "Erstansprache — Marketing-OS",
        "slug": "intro-marketing-os",
        "subject": "Wie wir {company} bei der Lead-Gewinnung unterstützen",
        "html_content": (
            "<p>Hallo {first_name},</p>"
            "<p>ich bin auf {company} aufmerksam geworden und hatte den "
            "Eindruck, dass Sie aktiv im Vertrieb skalieren wollen. "
            "Bei go4-automate haben wir eine Plattform gebaut, die "
            "Lead-Generierung, KI-Anreicherung und Multi-Channel-"
            "Engagement aus einer Hand liefert.</p>"
            "<p>Hätten Sie 15 Min für ein Kennenlerngespräch?</p>"
            "<p>Beste Grüße<br>{owner_name}</p>"
        ),
        "category": "outreach",
    },
    {
        "name": "Follow-up — Demo-Termin",
        "slug": "followup-demo",
        "subject": "Re: Marketing-Automation für {company}",
        "html_content": (
            "<p>Hallo {first_name},</p>"
            "<p>nur eine kurze Erinnerung — passt der Termin am "
            "<strong>{meeting_date}</strong> noch für Sie? Falls nicht, "
            "schicken Sie mir gerne 2-3 Alternativen.</p>"
            "<p>Beste Grüße<br>{owner_name}</p>"
        ),
        "category": "followup",
    },
    {
        "name": "Angebot zugeschickt",
        "slug": "offer-sent",
        "subject": "Ihr Angebot von go4-automate",
        "html_content": (
            "<p>Hallo {first_name},</p>"
            "<p>im Anhang finden Sie unser Angebot für {company}. "
            "Bei Fragen melden Sie sich jederzeit — ich rufe gerne "
            "auch zurück.</p>"
            "<p>Beste Grüße<br>{owner_name}</p>"
        ),
        "category": "sales",
    },
]


# ---------------------------------------------------------------------------
# Seed entry point
# ---------------------------------------------------------------------------


async def seed_demo_workspace(
    db: AsyncSession, *, tenant_id: str, owner_id: int | None = None
) -> dict[str, int]:
    """Create the demo workspace fixtures for ``tenant_id``.

    Idempotent: detects a previous seed via the demo-tagged company and
    returns counts of zero on re-runs. Caller is responsible for the
    surrounding transaction (we flush, not commit).

    Returns a dict of {entity: count_created} for caller logging / UI.
    """
    if await _already_seeded(db, tenant_id):
        logger.info("Demo workspace already seeded for {t}", t=tenant_id)
        return {
            "companies": 0, "contacts": 0,
            "pipelines": 0, "stages": 0, "deals": 0, "templates": 0,
        }

    pipeline, stages = await _seed_pipeline(db, tenant_id)
    companies_by_name = await _seed_companies(db, tenant_id, owner_id)
    contacts = await _seed_contacts(db, tenant_id, companies_by_name, owner_id)
    deals = await _seed_deals(
        db, tenant_id, pipeline, stages, companies_by_name, contacts, owner_id
    )
    templates = await _seed_email_templates(db, tenant_id)

    await db.flush()
    counts = {
        "companies": len(companies_by_name),
        "contacts": len(contacts),
        "pipelines": 1,
        "stages": len(stages),
        "deals": len(deals),
        "templates": len(templates),
    }
    logger.info(
        "Demo workspace seeded for {t}: {counts}", t=tenant_id, counts=counts
    )
    return counts


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


async def _already_seeded(db: AsyncSession, tenant_id: str) -> bool:
    """Detect a previous seed by looking for one of our fixture company
    names. Uses plain column equality (works on both Postgres and SQLite —
    JSONB containment operators are PG-only)."""
    fixture_names = [spec["name"] for spec in _COMPANIES]
    result = await db.execute(
        select(Company.id).where(
            Company.tenant_id == tenant_id,
            Company.name.in_(fixture_names),
        ).limit(1)
    )
    return result.first() is not None


async def _seed_pipeline(
    db: AsyncSession, tenant_id: str
) -> tuple[CrmPipeline, dict[str, CrmPipelineStage]]:
    pipeline = CrmPipeline(
        tenant_id=tenant_id,
        name="Demo-Vertriebspipeline",
        is_default=True,
        color="#0EA5E9",
        description="Beispiel-Pipeline mit 6 Stages — kann angepasst werden.",
    )
    db.add(pipeline)
    await db.flush()

    stages_by_name: dict[str, CrmPipelineStage] = {}
    for name, position, probability, color, is_won, is_lost in _PIPELINE_STAGES:
        stage = CrmPipelineStage(
            tenant_id=tenant_id,
            pipeline_id=pipeline.id,
            name=name,
            position=position,
            probability=probability,
            color=color,
            is_won=is_won,
            is_lost=is_lost,
        )
        db.add(stage)
        stages_by_name[name] = stage
    await db.flush()
    return pipeline, stages_by_name


async def _seed_companies(
    db: AsyncSession, tenant_id: str, owner_id: int | None
) -> dict[str, Company]:
    out: dict[str, Company] = {}
    for spec in _COMPANIES:
        company = Company(
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=spec["name"],
            domain=spec["domain"],
            website=f"https://{spec['domain']}",
            industry=spec["industry"],
            size=spec["size"],
            description=spec["description"],
            tags=[DEMO_TAG, spec["industry"].lower()],
        )
        db.add(company)
        out[spec["name"]] = company
    await db.flush()
    return out


async def _seed_contacts(
    db: AsyncSession,
    tenant_id: str,
    companies_by_name: dict[str, Company],
    owner_id: int | None,
) -> list[Contact]:
    contacts: list[Contact] = []
    for company_name, contact_specs in _CONTACTS_BY_COMPANY.items():
        company = companies_by_name.get(company_name)
        if company is None:
            continue
        for first, last, email, position in contact_specs:
            contact = Contact(
                tenant_id=tenant_id,
                company_id=company.id,
                owner_id=owner_id,
                name=f"{first} {last}",
                email=email,
                position=position,
                source="demo",
                tags=[DEMO_TAG],
            )
            db.add(contact)
            contacts.append(contact)
    await db.flush()
    return contacts


async def _seed_deals(
    db: AsyncSession,
    tenant_id: str,
    pipeline: CrmPipeline,
    stages: dict[str, CrmPipelineStage],
    companies_by_name: dict[str, Company],
    contacts: list[Contact],
    owner_id: int | None,
) -> list[CrmDeal]:
    contacts_by_company = {c.company_id: c for c in contacts}
    deals: list[CrmDeal] = []
    today = date.today()
    now = datetime.utcnow()
    for title, company_name, stage_name, value, days in _DEALS:
        company = companies_by_name.get(company_name)
        stage = stages.get(stage_name)
        if company is None or stage is None:
            continue
        contact = contacts_by_company.get(company.id)
        deal = CrmDeal(
            tenant_id=tenant_id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            owner_id=owner_id,
            company_id=company.id,
            contact_id=contact.id if contact else None,
            title=title,
            value=Decimal(value),
            currency="EUR",
            probability=stage.probability,
            expected_close=today + timedelta(days=days),
            status="won" if stage.is_won else ("lost" if stage.is_lost else "open"),
            won_at=now if stage.is_won else None,
            tags=[DEMO_TAG],
        )
        db.add(deal)
        deals.append(deal)
    await db.flush()
    return deals


async def _seed_email_templates(
    db: AsyncSession, tenant_id: str
) -> list[EmailTemplate]:
    templates: list[EmailTemplate] = []
    for spec in _EMAIL_TEMPLATES:
        template = EmailTemplate(
            tenant_id=tenant_id,
            name=spec["name"],
            slug=spec["slug"],
            subject=spec["subject"],
            html_content=spec["html_content"],
            variables=["first_name", "company", "owner_name"],
            category=spec["category"],
            tags=[DEMO_TAG],
        )
        db.add(template)
        templates.append(template)
    await db.flush()
    return templates


__all__ = ["DEMO_TAG", "seed_demo_workspace"]
