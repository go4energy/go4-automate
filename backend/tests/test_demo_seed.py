"""Tests for the demo workspace seeder."""

from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_seed_creates_full_workspace(db_session):
    """First call writes the expected fixtures."""
    from app.setup.demo_seed import seed_demo_workspace

    counts = await seed_demo_workspace(db_session, tenant_id="go4energy")
    assert counts == {
        "companies": 5,
        "contacts": 15,
        "pipelines": 1,
        "stages": 6,
        "deals": 5,
        "templates": 3,
    }


@pytest.mark.anyio
async def test_seed_is_idempotent(db_session):
    """Re-running on the same tenant returns zero counts and writes nothing."""
    from sqlalchemy import select

    from app.contacts.models import Company
    from app.setup.demo_seed import seed_demo_workspace

    await seed_demo_workspace(db_session, tenant_id="go4energy")
    rows_after_first = (
        await db_session.execute(
            select(Company).where(Company.tenant_id == "go4energy")
        )
    ).scalars().all()

    counts = await seed_demo_workspace(db_session, tenant_id="go4energy")
    assert counts == {
        "companies": 0, "contacts": 0,
        "pipelines": 0, "stages": 0, "deals": 0, "templates": 0,
    }

    rows_after_second = (
        await db_session.execute(
            select(Company).where(Company.tenant_id == "go4energy")
        )
    ).scalars().all()
    assert len(rows_after_first) == len(rows_after_second)


@pytest.mark.anyio
async def test_seed_isolated_per_tenant(db_session):
    """Seeding tenant A leaves tenant B untouched (and vice versa)."""
    from sqlalchemy import select

    from app.contacts.models import Company

    # Need a second tenant in the test DB before seeding it
    from app.models.tenant import Tenant
    from app.setup.demo_seed import seed_demo_workspace
    db_session.add(Tenant(tenant_id="other-tenant", tenant_name="Other", config={}))
    await db_session.flush()

    await seed_demo_workspace(db_session, tenant_id="go4energy")
    a_companies = (
        await db_session.execute(
            select(Company).where(Company.tenant_id == "go4energy")
        )
    ).scalars().all()
    b_companies = (
        await db_session.execute(
            select(Company).where(Company.tenant_id == "other-tenant")
        )
    ).scalars().all()
    assert len(a_companies) == 5
    assert len(b_companies) == 0


@pytest.mark.anyio
async def test_seeded_pipeline_has_six_stages(db_session):
    """The seeded sales pipeline must have exactly the 6 expected stages
    in correct order."""
    from sqlalchemy import select

    from app.crm.models import CrmPipeline, CrmPipelineStage
    from app.setup.demo_seed import seed_demo_workspace

    await seed_demo_workspace(db_session, tenant_id="go4energy")
    pipeline = (
        await db_session.execute(
            select(CrmPipeline).where(CrmPipeline.tenant_id == "go4energy")
        )
    ).scalar_one()
    assert pipeline.is_default is True

    stages = (
        await db_session.execute(
            select(CrmPipelineStage)
            .where(CrmPipelineStage.pipeline_id == pipeline.id)
            .order_by(CrmPipelineStage.position)
        )
    ).scalars().all()
    assert [s.name for s in stages] == [
        "Erstkontakt", "Qualifiziert", "Angebot",
        "Verhandlung", "Gewonnen", "Verloren",
    ]
    won = next(s for s in stages if s.is_won)
    lost = next(s for s in stages if s.is_lost)
    assert won.name == "Gewonnen"
    assert lost.name == "Verloren"


@pytest.mark.anyio
async def test_seeded_deals_distributed_across_stages(db_session):
    """Demo deals must hit at least 4 different stages so the pipeline
    UI looks alive."""
    from sqlalchemy import select

    from app.crm.models import CrmDeal, CrmPipelineStage
    from app.setup.demo_seed import seed_demo_workspace

    await seed_demo_workspace(db_session, tenant_id="go4energy")
    deals = (
        await db_session.execute(
            select(CrmDeal).where(CrmDeal.tenant_id == "go4energy")
        )
    ).scalars().all()
    stage_names = set()
    for d in deals:
        stage = (
            await db_session.execute(
                select(CrmPipelineStage).where(CrmPipelineStage.id == d.stage_id)
            )
        ).scalar_one()
        stage_names.add(stage.name)
    assert len(stage_names) >= 4
