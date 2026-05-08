"""Tests for generic tag-based auto-enrollment + forward-lead handling.

Covers the 8 verification scenarios from the implementation plan:
1. Frische Anmeldung ohne ref-Code (Google etc.)
2. Multi-Match (Lead in mehreren Pipelines parallel)
3. Custom-Field-Filter
4. Negativ-Filter (tags_none)
5. Forward erkannt + verarbeitet
6. Cold-Mail-Empfänger meldet sich selbst an (Self-Signup-Upgrade)
7. Tag-Update via Re-Identify (idempotent)
8. Cross-Domain (kein Forward)

Plus pure-function tests für AutoEnrollmentRouter._filter_matches.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.contacts.models import Contact
from app.engagement.auto_enrollment_router import AutoEnrollmentRouter
from app.engagement.models import EngagementPipeline, PipelineEnrollment
from tests.conftest import TEST_AUTH_HEADERS


TENANT_HEADERS = {**TEST_AUTH_HEADERS, "X-Tenant-ID": "go4energy"}


@pytest_asyncio.fixture
async def tenant(client):
    """Ensure go4energy tenant exists."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "go4energy", "tenant_name": "go4energy"},
    )
    assert response.status_code in (201, 409)
    return "go4energy"


@pytest_asyncio.fixture
async def api_key_headers():
    """Headers for external tracking API."""
    from app.config import settings

    settings.tracking_api_key = "test-tracking-key"
    settings.tracking_api_keys = {}
    return {"Authorization": "Bearer test-tracking-key"}


def _make_contact(tenant_id="go4energy", email="x@firma.de", name="X", **kw):
    """Build a Contact instance for filter-match tests (no DB)."""
    return Contact(
        tenant_id=tenant_id,
        email=email,
        name=name,
        tags=kw.get("tags", []),
        custom_fields=kw.get("custom_fields", {}),
    )


# ============== Pure Filter-Match Tests (no DB) ==============


def test_filter_matches_tags_any():
    f = {"tags_any": ["fachpartner", "elektriker"]}
    assert AutoEnrollmentRouter._filter_matches(f, _make_contact(tags=["fachpartner"]))
    assert AutoEnrollmentRouter._filter_matches(f, _make_contact(tags=["elektriker"]))
    assert not AutoEnrollmentRouter._filter_matches(f, _make_contact(tags=["andere"]))
    assert not AutoEnrollmentRouter._filter_matches(f, _make_contact(tags=[]))


def test_filter_matches_tags_all():
    f = {"tags_all": ["fachpartner", "leadgen"]}
    assert AutoEnrollmentRouter._filter_matches(
        f, _make_contact(tags=["fachpartner", "leadgen"])
    )
    assert not AutoEnrollmentRouter._filter_matches(
        f, _make_contact(tags=["fachpartner"])
    )
    assert AutoEnrollmentRouter._filter_matches(
        f, _make_contact(tags=["fachpartner", "leadgen", "extra"])
    )


def test_filter_matches_tags_none():
    f = {"tags_any": ["fachpartner"], "tags_none": ["unqualified"]}
    assert AutoEnrollmentRouter._filter_matches(
        f, _make_contact(tags=["fachpartner"])
    )
    assert not AutoEnrollmentRouter._filter_matches(
        f, _make_contact(tags=["fachpartner", "unqualified"])
    )


def test_filter_matches_custom_fields():
    f = {"tags_any": ["fachpartner"], "custom_fields": {"region": "Bayern"}}
    assert AutoEnrollmentRouter._filter_matches(
        f,
        _make_contact(tags=["fachpartner"], custom_fields={"region": "Bayern"}),
    )
    assert not AutoEnrollmentRouter._filter_matches(
        f,
        _make_contact(tags=["fachpartner"], custom_fields={"region": "NRW"}),
    )
    assert not AutoEnrollmentRouter._filter_matches(
        f,
        _make_contact(tags=["fachpartner"], custom_fields={}),
    )


def test_filter_matches_empty_filter_no_match():
    """Empty filter should NOT match anyone (manual-only pipeline)."""
    assert not AutoEnrollmentRouter._filter_matches({}, _make_contact(tags=["x"]))
    assert not AutoEnrollmentRouter._filter_matches(None, _make_contact(tags=["x"]))


# ============== End-to-End via /tracking/identify ==============


async def _create_pipeline_with_filter(client, slug, name, filter_spec):
    """Helper: create pipeline with auto_enroll_filter via API."""
    resp = await client.post(
        "/api/v1/engagement/pipelines",
        json={
            "name": name,
            "slug": slug,
            "channels": ["email"],
            "auto_enroll_filter": filter_spec,
        },
        headers=TENANT_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _identify(client, headers, **payload):
    return await client.post(
        "/api/v1/tracking/identify", json=payload, headers=headers
    )


@pytest.mark.anyio
async def test_scenario_1_fresh_signup_single_match(
    client, tenant, api_key_headers, db_session
):
    """Frische Anmeldung ohne ref-Code → enrolled in matchender Pipeline."""
    pid = await _create_pipeline_with_filter(
        client,
        "inbound-fp-1",
        "Inbound Fachpartner",
        {"tags_any": ["fachpartner"]},
    )

    resp = await _identify(
        client,
        api_key_headers,
        email="neu1@firma.de",
        name="Hans Neu",
        tags=["fachpartner"],
        source="website_form",
    )
    assert resp.status_code == 200
    contact_id = resp.json()["lead_id"]

    result = await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == contact_id,
            PipelineEnrollment.pipeline_id == pid,
        )
    )
    enr = result.scalar_one_or_none()
    assert enr is not None
    assert enr.stage == "engaged"
    assert enr.status == "active"


@pytest.mark.anyio
async def test_scenario_2_multi_match_parallel(
    client, tenant, api_key_headers, db_session
):
    """Lead mit zwei Tags → enrolled in BEIDEN Pipelines parallel."""
    p1 = await _create_pipeline_with_filter(
        client, "inbound-fp-2", "Inbound Fachpartner",
        {"tags_any": ["fachpartner"]},
    )
    p2 = await _create_pipeline_with_filter(
        client, "demo-walkthrough-2", "Demo-Walkthrough",
        {"tags_all": ["demo"]},
    )

    resp = await _identify(
        client, api_key_headers,
        email="multi@firma.de", name="Multi", tags=["fachpartner", "demo"],
    )
    assert resp.status_code == 200
    cid = resp.json()["lead_id"]

    result = await db_session.execute(
        select(PipelineEnrollment.pipeline_id).where(
            PipelineEnrollment.contact_id == cid
        )
    )
    pipeline_ids = {row[0] for row in result.all()}
    assert p1 in pipeline_ids
    assert p2 in pipeline_ids


@pytest.mark.anyio
async def test_scenario_3_custom_field_filter(
    client, tenant, api_key_headers, db_session
):
    """Custom-Field-Bedingung: nur Bayern enrollt."""
    pid = await _create_pipeline_with_filter(
        client, "bayern-premium-3", "Bayern Premium",
        {"tags_all": ["fachpartner"], "custom_fields": {"region": "Bayern"}},
    )

    # Match
    r1 = await _identify(
        client, api_key_headers,
        email="bay@firma.de", name="Bay",
        tags=["fachpartner"], custom_fields={"region": "Bayern"},
    )
    cid_match = r1.json()["lead_id"]
    rows = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == cid_match,
            PipelineEnrollment.pipeline_id == pid,
        )
    )).scalar_one_or_none()
    assert rows is not None

    # No match
    r2 = await _identify(
        client, api_key_headers,
        email="nrw@firma.de", name="NRW",
        tags=["fachpartner"], custom_fields={"region": "NRW"},
    )
    cid_no = r2.json()["lead_id"]
    rows2 = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == cid_no,
            PipelineEnrollment.pipeline_id == pid,
        )
    )).scalar_one_or_none()
    assert rows2 is None


@pytest.mark.anyio
async def test_scenario_4_negative_filter(
    client, tenant, api_key_headers, db_session
):
    """tags_none: unqualifizierte Leads landen NICHT in der Pipeline."""
    pid = await _create_pipeline_with_filter(
        client, "std-inbound-4", "Standard Inbound",
        {"tags_any": ["fachpartner"], "tags_none": ["unqualified"]},
    )

    resp = await _identify(
        client, api_key_headers,
        email="unq@firma.de", name="Unqualifiziert",
        tags=["fachpartner", "unqualified"],
    )
    cid = resp.json()["lead_id"]
    rows = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == cid,
            PipelineEnrollment.pipeline_id == pid,
        )
    )).scalar_one_or_none()
    assert rows is None


@pytest.mark.anyio
async def test_scenario_5_forward_detected(
    client, tenant, api_key_headers, db_session
):
    """Forward (gleiche Domain): Original-Enrollment stop, neuer Contact."""
    # Setup Müller
    r0 = await _identify(
        client, api_key_headers,
        email="mueller@elektrofirma.de", name="Hans Müller", source="cold_outreach",
    )
    mueller_id = r0.json()["lead_id"]
    mueller_hash = r0.json()["tracking_hash"]

    # Müller manuell in Pipeline X enrollten (Cold-Outreach)
    cold_pid = await _create_pipeline_with_filter(
        client, "cold-outreach-5", "Cold Outreach", None,
    )
    # Update pipeline auto_enroll_filter to None (no filter)
    await client.put(
        f"/api/v1/engagement/pipelines/{cold_pid}",
        json={"auto_enroll_filter": None},
        headers=TENANT_HEADERS,
    )

    enroll = PipelineEnrollment(
        tenant_id="go4energy",
        contact_id=mueller_id,
        pipeline_id=cold_pid,
        stage="lead",
        status="active",
    )
    db_session.add(enroll)
    await db_session.flush()
    await db_session.commit()

    # Meier identifiziert sich mit Müllers Hash, eigene Email, gleiche Domain
    r1 = await _identify(
        client, api_key_headers,
        email="meier@elektrofirma.de", name="Otto Meier",
        existing_hash=mueller_hash,
        tags=["fachpartner"],
    )
    assert r1.status_code == 200
    meier_id = r1.json()["lead_id"]
    assert meier_id != mueller_id

    # Drop ORM cache so SELECTs see the updates from the HTTP-handler session
    db_session._session.expire_all()

    # Verify Meier-Contact has source_contact_id = mueller
    meier = (await db_session.execute(
        select(Contact).where(Contact.id == meier_id)
    )).scalar_one()
    assert meier.source_contact_id == mueller_id

    # Verify Müllers Email unverändert
    mueller = (await db_session.execute(
        select(Contact).where(Contact.id == mueller_id)
    )).scalar_one()
    assert mueller.email == "mueller@elektrofirma.de"
    assert mueller.name == "Hans Müller"

    # Verify Müllers Enrollment stopped
    enr = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == mueller_id,
            PipelineEnrollment.pipeline_id == cold_pid,
        )
    )).scalar_one()
    assert enr.status == "stopped"
    assert enr.stopped_reason == "forwarded_to_colleague"


@pytest.mark.anyio
async def test_scenario_6_self_signup_upgrade(
    client, tenant, api_key_headers, db_session
):
    """Cold-Mail-Empfänger meldet sich selbst an → engaged-Upgrade."""
    # Müller anlegen + manuell in Pipeline mit stage='lead'
    r0 = await _identify(
        client, api_key_headers,
        email="selfsignup@elektrofirma.de", name="Müller",
    )
    mueller_id = r0.json()["lead_id"]

    cold_pid = await _create_pipeline_with_filter(
        client, "cold-out-6", "Cold Out", None,
    )
    await client.put(
        f"/api/v1/engagement/pipelines/{cold_pid}",
        json={"auto_enroll_filter": None},
        headers=TENANT_HEADERS,
    )
    enr_init = PipelineEnrollment(
        tenant_id="go4energy",
        contact_id=mueller_id,
        pipeline_id=cold_pid,
        stage="lead",
        status="active",
    )
    db_session.add(enr_init)
    await db_session.commit()

    # Self-Signup
    r1 = await _identify(
        client, api_key_headers,
        email="selfsignup@elektrofirma.de", name="Müller",
        tags=["fachpartner"],
    )
    assert r1.status_code == 200

    db_session._session.expire_all()

    # Müllers Enrollment ist jetzt 'engaged'
    enr = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == mueller_id,
            PipelineEnrollment.pipeline_id == cold_pid,
        )
    )).scalar_one()
    assert enr.stage == "engaged"


@pytest.mark.anyio
async def test_scenario_7_tag_update_idempotent(
    client, tenant, api_key_headers, db_session
):
    """Tag-Update via Re-Identify: bereits enrolled, neue Pipeline kommt dazu."""
    p_fp = await _create_pipeline_with_filter(
        client, "inb-fp-7", "Inb FP", {"tags_any": ["fachpartner"]},
    )
    p_demo = await _create_pipeline_with_filter(
        client, "demo-7", "Demo", {"tags_all": ["demo"]},
    )

    # Erster Identify → nur fachpartner
    r1 = await _identify(
        client, api_key_headers,
        email="repeat7@firma.de", name="Repeat", tags=["fachpartner"],
    )
    cid = r1.json()["lead_id"]

    # Zweiter Identify → demo dazu
    r2 = await _identify(
        client, api_key_headers,
        email="repeat7@firma.de", name="Repeat", tags=["demo"],
    )
    assert r2.json()["lead_id"] == cid

    # Beide Pipelines aktiv, je 1 Enrollment
    rows = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == cid
        )
    )).scalars().all()
    pipeline_ids = [r.pipeline_id for r in rows]
    assert pipeline_ids.count(p_fp) == 1
    assert pipeline_ids.count(p_demo) == 1


@pytest.mark.anyio
async def test_scenario_8_cross_domain_no_forward(
    client, tenant, api_key_headers, db_session
):
    """Verschiedene Domains → kein Forward, kein Stop von Original."""
    r0 = await _identify(
        client, api_key_headers,
        email="boss@firma-a.de", name="Boss",
    )
    boss_id = r0.json()["lead_id"]
    boss_hash = r0.json()["tracking_hash"]

    cold_pid = await _create_pipeline_with_filter(
        client, "cold-out-8", "Cold Out", None,
    )
    await client.put(
        f"/api/v1/engagement/pipelines/{cold_pid}",
        json={"auto_enroll_filter": None},
        headers=TENANT_HEADERS,
    )
    enr = PipelineEnrollment(
        tenant_id="go4energy",
        contact_id=boss_id,
        pipeline_id=cold_pid,
        stage="lead",
        status="active",
    )
    db_session.add(enr)
    await db_session.commit()

    # Identify mit Hash + andere Domain
    r1 = await _identify(
        client, api_key_headers,
        email="external@andere-firma.de", name="External",
        existing_hash=boss_hash,
    )
    external_id = r1.json()["lead_id"]
    assert external_id != boss_id

    db_session._session.expire_all()

    # External hat KEINE source_contact_id
    ext = (await db_session.execute(
        select(Contact).where(Contact.id == external_id)
    )).scalar_one()
    assert ext.source_contact_id is None

    # Boss-Enrollment unverändert
    boss_enr = (await db_session.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.contact_id == boss_id,
        )
    )).scalar_one()
    assert boss_enr.status == "active"
    assert boss_enr.stopped_reason is None
