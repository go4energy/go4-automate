"""Tests for the leadgen-contacts pipeline.

Coverage:
- Name normalisation + title stripping
- Gender library + LLM fallback shape
- Impressum-scraper LinkedIn link extraction
- Apollo CSV row layout
- tracking_hash assignment during engagement handoff
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import select

from app.contacts.models import Contact
from app.contacts.utils import generate_tracking_hash
from app.leadgen.contact_normalize import (
    from_managing_director_string,
    from_primary_contact_dict,
    normalize_full_name,
    split_name,
)
from app.leadgen.gender import guess_gender_from_first_name, salutation_for
from app.leadgen.impressum_scraper import parse_impressum_html
from app.leadgen.linkedin_search import (
    _has_firm_slug,
    _is_linkedin_host,
    _normalise as _ls_normalise,
    _score_person_match,
)
from app.leadgen.models import LeadgenImpressum, LeadgenLLMInsights, LeadgenPlace

HEADERS = {"X-Tenant-ID": "go4energy"}


# ---------------- Name normalisation ----------------


def test_split_name_strips_academic_titles():
    assert split_name("Dr. Max Mustermann") == ("Max", "Mustermann")
    assert split_name("Prof. Dr. Sabine Müller") == ("Sabine", "Müller")
    # Hyphenated title is not in the strip-list — the parser keeps it as the
    # first token so the user can either extend _TITLE_TOKENS or accept the
    # imperfect split. Documented here as the current behaviour.
    assert split_name("Dipl.-Ing. Klaus Schmidt") == ("Dipl.-Ing.", "Klaus Schmidt")
    assert split_name("Anna Berger") == ("Anna", "Berger")
    assert split_name("Herr Lukas Weber") == ("Lukas", "Weber")
    # Empty / single-token / garbage inputs degrade gracefully.
    assert split_name("") == ("", "")
    assert split_name("X") == ("X", "")


def test_normalize_full_name_collapses_whitespace():
    assert normalize_full_name("  Max   Mustermann  ") == "Max Mustermann"
    assert normalize_full_name("\tSabine\nMüller") == "Sabine Müller"
    assert normalize_full_name("") == ""


def test_from_managing_director_string_canonicalises_name():
    payload = from_managing_director_string("Dr. Max Mustermann")
    assert payload is not None
    assert payload["first_name"] == "Max"
    assert payload["last_name"] == "Mustermann"
    # Title-stripped form keeps the unique-key dedup honest.
    assert payload["full_name"] == "Max Mustermann"
    assert payload["source"] == "managing_director"


def test_from_managing_director_string_returns_none_for_empty():
    assert from_managing_director_string("") is None
    assert from_managing_director_string("   ") is None


def test_from_primary_contact_dict_honours_legacy_gender():
    payload = from_primary_contact_dict(
        {
            "first_name": "Sabine",
            "last_name": "Müller",
            "salutation": "Frau",
            "role": "Vertrieb",
        }
    )
    assert payload["gender"] == "female"
    assert payload["gender_method"] == "jsonb_legacy"
    assert payload["role"] == "Vertrieb"


def test_from_primary_contact_dict_returns_none_when_no_name():
    assert from_primary_contact_dict({}) is None
    assert from_primary_contact_dict(None) is None


# ---------------- Gender detection ----------------


def test_guess_gender_unambiguous_dach_names():
    g, conf, method = guess_gender_from_first_name("Maximilian")
    assert g == "male" and method == "library" and conf == 1.0
    g, conf, method = guess_gender_from_first_name("Sabine")
    assert g == "female" and method == "library"


def test_guess_gender_ambiguous_returns_unknown():
    g, conf, method = guess_gender_from_first_name("")
    assert g is None and method == "unknown"


def test_salutation_respects_confidence_floor():
    assert salutation_for("male", 1.0) == "Herr"
    assert salutation_for("female", 0.7) == "Frau"
    # Below the floor we degrade to neutral so templating can fall back.
    assert salutation_for("male", 0.5) is None
    assert salutation_for(None, 1.0) is None


# ---------------- Impressum LinkedIn link extraction ----------------


_IMPRESSUM_HTML = """
<html><body>
<h1>Impressum</h1>
<p>Geschäftsführer: Max Mustermann</p>
<p>Email: info@example.de</p>
<a href="https://www.linkedin.com/in/max-mustermann-12345/">Max auf LinkedIn</a>
<a href="https://de.linkedin.com/in/sabine-mueller-67890?utm=test">Sabine</a>
<a href="https://www.linkedin.com/company/example-gmbh/">Firma auf LinkedIn</a>
</body></html>
"""


def test_parse_impressum_extracts_linkedin_company_url():
    data = parse_impressum_html(_IMPRESSUM_HTML, "https://example.de/impressum")
    assert data.linkedin_company_url == "https://www.linkedin.com/company/example-gmbh"


def test_parse_impressum_extracts_person_links_with_text():
    data = parse_impressum_html(_IMPRESSUM_HTML, "https://example.de/impressum")
    urls = [p["url"] for p in data.linkedin_person_links]
    assert "https://www.linkedin.com/in/max-mustermann-12345" in urls
    # utm parameter is stripped during normalisation.
    assert "https://de.linkedin.com/in/sabine-mueller-67890" in urls


def test_parse_impressum_no_linkedin_returns_empty():
    data = parse_impressum_html("<html><body>nichts</body></html>", "https://x")
    assert data.linkedin_company_url is None
    assert data.linkedin_person_links == []


# ---------------- LinkedIn-search heuristics ----------------


def test_linkedin_url_normalisation_strips_query_and_trailing_slash():
    assert _ls_normalise("https://www.linkedin.com/in/foo/?utm=1") == (
        "https://www.linkedin.com/in/foo"
    )
    assert _ls_normalise("https://www.linkedin.com/in/foo/#about") == (
        "https://www.linkedin.com/in/foo"
    )


def test_person_match_score_credits_full_name_hit():
    score = _score_person_match(
        title="Max Mustermann – Geschäftsführer",
        snippet="Beispiel GmbH",
        first_name="Max",
        last_name="Mustermann",
        company="Beispiel GmbH",
    )
    # First+Last+Company all match → max score 1.0.
    assert score == 1.0


def test_linkedin_host_whitelist_rejects_foreign_locales():
    """Pilot run accepted ua.linkedin.com hits — those must be rejected now."""
    assert _is_linkedin_host("https://www.linkedin.com/company/foo") is True
    assert _is_linkedin_host("https://de.linkedin.com/company/foo") is True
    assert _is_linkedin_host("https://at.linkedin.com/in/foo") is True
    assert _is_linkedin_host("https://ch.linkedin.com/in/foo") is True
    # Localised LinkedIn pages are not useful for German B2B outreach.
    assert _is_linkedin_host("https://ua.linkedin.com/company/foo") is False
    assert _is_linkedin_host("https://ru.linkedin.com/in/foo") is False
    assert _is_linkedin_host("https://cn.linkedin.com/company/foo") is False
    # Non-LinkedIn URLs short-circuit safely.
    assert _is_linkedin_host("https://example.de") is False


def test_firm_slug_rejection_marks_company_in_slugs():
    """Pilot run accepted ``/in/eab-elektro-anlagen-bau-gmbh`` as a person URL.

    The slug detector must catch the well-known Rechtsformen so person
    matching skips them altogether.
    """
    assert _has_firm_slug("https://de.linkedin.com/in/eab-elektro-anlagen-bau-gmbh") is True
    assert _has_firm_slug("https://de.linkedin.com/in/foo-ohg") is True
    assert _has_firm_slug("https://de.linkedin.com/in/bar-kg") is True
    assert _has_firm_slug("https://de.linkedin.com/in/baz-ag") is True
    # Real person slugs must pass.
    assert _has_firm_slug("https://de.linkedin.com/in/max-mustermann") is False
    assert _has_firm_slug("https://de.linkedin.com/in/jens-krannich-124789161") is False


def test_person_match_score_partial_hit_below_threshold():
    score = _score_person_match(
        title="Andere Person – ganz andere Firma",
        snippet="",
        first_name="Max",
        last_name="Mustermann",
        company="Beispiel GmbH",
    )
    # No overlap → 0; the worker uses score >= 0.5 as the accept threshold.
    assert score < 0.5


# ---------------- generate_tracking_hash ----------------


def test_generate_tracking_hash_default_length_is_12():
    h = generate_tracking_hash()
    assert len(h) == 12
    assert re.fullmatch(r"[A-Za-z0-9]{12}", h)


def test_generate_tracking_hash_respects_length_argument():
    assert len(generate_tracking_hash(8)) == 8
    assert len(generate_tracking_hash(20)) == 20


def test_generate_tracking_hash_is_random():
    # 1000 hashes must be unique with overwhelming probability — birthday
    # bound at 62**12 keeps the collision probability < 10⁻¹⁵.
    hashes = {generate_tracking_hash() for _ in range(1000)}
    assert len(hashes) == 1000


# ---------------- Engagement handoff: tracking_hash assignment ----------------


@pytest.mark.anyio
async def test_handoff_creates_contact_with_tracking_hash(client, db_session):
    """Tipping a leadgen place into the engagement funnel must populate
    contacts.tracking_hash so customer-journey URLs can resolve back to the
    contact later. This is the end-to-end Plan B verification.
    """
    # 1. Campaign with auto-created engagement pipeline.
    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "HandoffHashTest",
            "slug": "handoff-hash-test",
            "queries": ["dummy"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]

    # 2. Plant a fully-enriched place (status=llm_done) with impressum + LLM
    #    insights so the handoff considers it eligible.
    place = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=cid,
        google_place_id="hh_test_1",
        name="HandoffTest GmbH",
        address_country="DE",
        status="llm_done",
        contact_id=None,
    )
    db_session.add(place)
    await db_session.flush()
    db_session.add(
        LeadgenImpressum(
            tenant_id="go4energy",
            place_id=place.id,
            email="kontakt-handoff@example.de",
            managing_directors=["Max Mustermann"],
        )
    )
    db_session.add(
        LeadgenLLMInsights(
            tenant_id="go4energy",
            place_id=place.id,
            target_match_score=10,
            services=["PV-Anlagen"],
            primary_contact={
                "first_name": "Max",
                "last_name": "Mustermann",
                "role": "Geschäftsführer",
            },
        )
    )
    await db_session.commit()

    # 3. Trigger handoff (min_score=0 so our score-10 row is always picked).
    h = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/handoff",
        headers=HEADERS,
        json={"min_score": 0, "limit": 10},
    )
    assert h.status_code == 200, h.text
    assert h.json()["contacts_created"] == 1

    # 4. Verify the resulting contact carries a tracking hash.
    contact = (
        await db_session.execute(
            select(Contact).where(
                Contact.tenant_id == "go4energy",
                Contact.email == "kontakt-handoff@example.de",
            )
        )
    ).scalar_one()
    assert contact.tracking_hash, "handoff must populate tracking_hash"
    assert re.fullmatch(r"[A-Za-z0-9]{12}", contact.tracking_hash)
    assert contact.source == "leadgen"


@pytest.mark.anyio
async def test_handoff_preserves_existing_tracking_hash(client, db_session):
    """Re-handing-off a place whose Contact already has a hash (e.g. because
    Odoo called /tracking/identify first) must keep the original hash so
    in-flight tracking links keep working.
    """
    # Pre-existing contact with a hash — simulates the Odoo-first scenario.
    pre_hash = "PreExisting12"
    pre_contact = Contact(
        tenant_id="go4energy",
        name="Vorhanden GmbH",
        email="reuse-handoff@example.de",
        tracking_hash=pre_hash,
    )
    db_session.add(pre_contact)
    await db_session.commit()  # release the SQLite write lock before HTTP

    # Campaign + place pointing at the same email.
    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "HandoffReuseTest",
            "slug": "handoff-reuse-test",
            "queries": ["dummy"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    place = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=cid,
        google_place_id="hh_test_reuse",
        name="Vorhanden GmbH",
        address_country="DE",
        status="llm_done",
    )
    db_session.add(place)
    await db_session.flush()
    db_session.add(
        LeadgenImpressum(
            tenant_id="go4energy",
            place_id=place.id,
            email="reuse-handoff@example.de",
            managing_directors=["Max Mustermann"],
        )
    )
    db_session.add(
        LeadgenLLMInsights(
            tenant_id="go4energy",
            place_id=place.id,
            target_match_score=9,
            services=["PV"],
        )
    )
    await db_session.commit()

    h = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/handoff",
        headers=HEADERS,
        json={"min_score": 0, "limit": 10},
    )
    assert h.status_code == 200, h.text
    assert h.json()["contacts_reused"] == 1

    refreshed = (
        await db_session.execute(
            select(Contact).where(Contact.email == "reuse-handoff@example.de")
        )
    ).scalar_one()
    assert refreshed.tracking_hash == pre_hash, (
        "existing hash must not be overwritten on re-handoff"
    )


# ---------------- Place detail: contacts + neighbors ----------------


@pytest.mark.anyio
async def test_place_response_includes_linkedin_and_contacts(client, db_session):
    """GET /places/{id} must surface place.linkedin_company_url + the eager-
    loaded leadgen_contacts list so the detail view has everything it needs
    in one round-trip.
    """
    from app.leadgen.models import LeadgenContact, LeadgenPlace

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "PlaceDetailShape",
            "slug": "place-detail-shape",
            "queries": ["x"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    place = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=cid,
        google_place_id="pd_test_1",
        name="DetailTest GmbH",
        status="llm_done",
        linkedin_company_url="https://www.linkedin.com/company/detailtest",
        linkedin_company_match_method="serper",
    )
    db_session.add(place)
    await db_session.flush()
    db_session.add(
        LeadgenContact(
            tenant_id="go4energy",
            place_id=place.id,
            first_name="Max",
            last_name="Mustermann",
            full_name="Max Mustermann",
            role="Geschäftsführer",
            linkedin_url="https://www.linkedin.com/in/max-mustermann",
            linkedin_match_method="impressum_link",
            linkedin_match_confidence=1.0,
            gender="male",
            gender_confidence=1.0,
            gender_method="library",
            source="managing_director",
        )
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/leadgen/places/{place.id}", headers=HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["linkedin_company_url"] == "https://www.linkedin.com/company/detailtest"
    assert body["linkedin_company_match_method"] == "serper"
    assert len(body["contacts"]) == 1
    contact = body["contacts"][0]
    assert contact["full_name"] == "Max Mustermann"
    assert contact["linkedin_url"] == "https://www.linkedin.com/in/max-mustermann"
    assert contact["gender"] == "male"


@pytest.mark.anyio
async def test_place_neighbors_returns_prev_next(client, db_session):
    """/places/{id}/neighbors walks the campaign's place list in the same
    sort order the campaign-list view used. Verifies the central case (place
    in the middle has both neighbors) and the edge cases (first/last).
    """
    from app.leadgen.models import LeadgenLLMInsights, LeadgenPlace

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "NeighborTest",
            "slug": "neighbor-test",
            "queries": ["x"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]

    # Three places with descending match scores.
    ids = []
    for i, score in enumerate([9, 7, 5]):
        p = LeadgenPlace(
            tenant_id="go4energy",
            campaign_id=cid,
            google_place_id=f"nb_{i}",
            name=f"Place {i}",
            status="llm_done",
        )
        db_session.add(p)
        await db_session.flush()
        db_session.add(
            LeadgenLLMInsights(
                tenant_id="go4energy",
                place_id=p.id,
                target_match_score=score,
            )
        )
        ids.append(p.id)
    await db_session.commit()

    # Sorted desc by match: [score=9, 7, 5] → ids in same order.
    r = await client.get(
        f"/api/v1/leadgen/places/{ids[1]}/neighbors",
        params={"order_by": "match", "order_dir": "desc"},
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prev_id"] == ids[0]
    assert body["next_id"] == ids[2]

    # First place: no prev.
    r0 = await client.get(
        f"/api/v1/leadgen/places/{ids[0]}/neighbors",
        params={"order_by": "match", "order_dir": "desc"},
        headers=HEADERS,
    )
    assert r0.json() == {"prev_id": None, "next_id": ids[1]}

    # Last place: no next.
    r2 = await client.get(
        f"/api/v1/leadgen/places/{ids[2]}/neighbors",
        params={"order_by": "match", "order_dir": "desc"},
        headers=HEADERS,
    )
    assert r2.json() == {"prev_id": ids[1], "next_id": None}


# ---------------- LinkedIn stage: resumability + max_override ----------------


async def _build_linkedin_stage_fixture(db_session, place_count: int = 3):
    """Plant a campaign + N already-llm-done places ready for the linkedin stage."""
    from app.leadgen.models import (
        LeadgenCampaign,
        LeadgenLLMInsights,
        LeadgenPlace,
        LeadgenRun,
    )

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="LinkedinFixture",
        slug=f"linkedin-fixture-{id(db_session)}",
        queries=["dummy"],
        source="google_places",
        source_config={},
    )
    db_session.add(campaign)
    await db_session.flush()

    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="linkedin",
        status="running",
        stage_state={"max_override": place_count},
    )
    db_session.add(run)
    await db_session.flush()

    places = []
    for i in range(place_count):
        p = LeadgenPlace(
            tenant_id="go4energy",
            campaign_id=campaign.id,
            run_id=run.id,
            google_place_id=f"li_test_{i}",
            name=f"Test GmbH {i}",
            address_country="DE",
            status="llm_done",
        )
        db_session.add(p)
        await db_session.flush()
        db_session.add(
            LeadgenLLMInsights(
                tenant_id="go4energy",
                place_id=p.id,
                target_match_score=8,
            )
        )
        places.append(p)
    await db_session.flush()
    return campaign, run, places


@pytest.mark.anyio
async def test_linkedin_stage_honors_max_override(db_session, monkeypatch):
    """state.max_override must cap the per-run place count even when the
    eligible pool is bigger. Crucial for the 'test on 100 first' workflow.
    """
    from app.leadgen import worker as worker_mod
    from app.leadgen.worker import _process_linkedin_stage

    # 5 eligible places, but max_override=3 → only 3 must be processed.
    campaign, run, places = await _build_linkedin_stage_fixture(db_session, 5)
    run.stage_state = {"max_override": 3}
    await db_session.flush()

    # Stub out Serper so the test doesn't hit the network.
    async def _no_serper(*_a, **_kw):
        return None, 0.0

    monkeypatch.setattr(worker_mod, "find_company_linkedin_url", _no_serper)
    monkeypatch.setattr(worker_mod, "find_person_linkedin_url", _no_serper)

    # No serper key in test env → company/person Serper calls short-circuit
    # via the `if serper_key:` guard, but we still want to verify the cap.
    monkeypatch.setattr(worker_mod.settings, "serper_api_key", "")

    class _NoLLM:
        async def generate_json(self, *a, **kw):
            return {}

    await _process_linkedin_stage(
        db_session,
        run=run,
        campaign=campaign,
        llm=_NoLLM(),
    )

    state = run.stage_state or {}
    assert state.get("places_processed") == 3, state
    # The remaining 2 places must NOT be marked processed.
    processed = sum(
        1 for p in places if (p.enrichment_flags or {}).get("linkedin_processed_at")
    )
    assert processed == 3


@pytest.mark.anyio
async def test_enrich_preview_counts_by_min_match_score(client, db_session):
    """The preview endpoint must reflect the (stages, min_match_score) combo
    that the operator picked in the modal — that's the only way the live
    counter is trustworthy.
    """
    from app.leadgen.models import LeadgenLLMInsights, LeadgenPlace

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "PreviewTest",
            "slug": "preview-test",
            "queries": ["x"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]

    # Plant 4 places with descending scores 9, 7, 5, 3.
    for i, score in enumerate([9, 7, 5, 3]):
        p = LeadgenPlace(
            tenant_id="go4energy",
            campaign_id=cid,
            google_place_id=f"prev_{i}",
            name=f"Place {i}",
            status="llm_done",
        )
        db_session.add(p)
        await db_session.flush()
        db_session.add(
            LeadgenLLMInsights(
                tenant_id="go4energy",
                place_id=p.id,
                target_match_score=score,
            )
        )
    await db_session.commit()

    # No filter → all 4.
    r = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich/preview",
        headers=HEADERS,
        json={"limit": 1, "stages": ["linkedin"]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["eligible_count"] == 4

    # min_match_score=7 → places with score 9 and 7.
    r = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich/preview",
        headers=HEADERS,
        json={"limit": 1, "stages": ["linkedin"], "min_match_score": 7},
    )
    assert r.json()["eligible_count"] == 2

    # min_match_score=10 → none.
    r = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich/preview",
        headers=HEADERS,
        json={"limit": 1, "stages": ["linkedin"], "min_match_score": 10},
    )
    assert r.json()["eligible_count"] == 0


@pytest.mark.anyio
async def test_linkedin_stage_skips_companies_when_disabled(db_session, monkeypatch):
    """Default (enrich_companies=False): no Serper call for the company URL.

    The whole point of the persons-only mode is to skip the per-place company
    query. This test guards that the worker honours state.enrich_companies.
    """
    from app.leadgen import worker as worker_mod
    from app.leadgen.models import LeadgenContact
    from app.leadgen.worker import _process_linkedin_stage

    campaign, run, places = await _build_linkedin_stage_fixture(db_session, 2)
    # Plant a contact so the persons-side has work to do.
    for p in places:
        db_session.add(
            LeadgenContact(
                tenant_id="go4energy",
                place_id=p.id,
                first_name="Max",
                last_name="Mustermann",
                full_name="Max Mustermann",
                source="managing_director",
            )
        )
    run.stage_state = {"max_override": 10}  # enrich_companies NOT set
    await db_session.commit()

    company_calls = {"n": 0}
    person_calls = {"n": 0}

    async def _track_company(*_a, **_kw):
        company_calls["n"] += 1
        return None, 0.0

    async def _track_person(*_a, **_kw):
        person_calls["n"] += 1
        return None, 0.0

    monkeypatch.setattr(worker_mod, "find_company_linkedin_url", _track_company)
    monkeypatch.setattr(worker_mod, "find_person_linkedin_url", _track_person)
    monkeypatch.setattr(worker_mod.settings, "serper_api_key", "fake-key")

    class _NoLLM:
        async def generate_json(self, *a, **kw):
            return {}

    await _process_linkedin_stage(
        db_session,
        run=run,
        campaign=campaign,
        llm=_NoLLM(),
    )

    assert company_calls["n"] == 0, "default mode must NOT call Serper for company URLs"
    assert person_calls["n"] >= 2, "person Serper calls still expected"


@pytest.mark.anyio
async def test_linkedin_stage_calls_companies_when_enabled(db_session, monkeypatch):
    """When enrich_companies=True the worker issues 1 company Serper call per
    place that doesn't already carry a linkedin_company_url.
    """
    from app.leadgen import worker as worker_mod
    from app.leadgen.worker import _process_linkedin_stage

    campaign, run, places = await _build_linkedin_stage_fixture(db_session, 2)
    run.stage_state = {"max_override": 10, "enrich_companies": True}
    await db_session.commit()

    company_calls = {"n": 0}

    async def _track_company(*_a, **_kw):
        company_calls["n"] += 1
        return None, 0.0

    async def _no_person(*_a, **_kw):
        return None, 0.0

    monkeypatch.setattr(worker_mod, "find_company_linkedin_url", _track_company)
    monkeypatch.setattr(worker_mod, "find_person_linkedin_url", _no_person)
    monkeypatch.setattr(worker_mod.settings, "serper_api_key", "fake-key")

    class _NoLLM:
        async def generate_json(self, *a, **kw):
            return {}

    await _process_linkedin_stage(
        db_session,
        run=run,
        campaign=campaign,
        llm=_NoLLM(),
    )

    assert company_calls["n"] == 2, (
        "enrich_companies=True must trigger one company Serper call per place"
    )


@pytest.mark.anyio
async def test_enrich_preview_returns_contact_count(client, db_session):
    """The preview endpoint must surface contact_count alongside eligible_count
    so the frontend can show 'X Firmen + Y Personen'.
    """
    from app.leadgen.models import LeadgenContact, LeadgenLLMInsights, LeadgenPlace

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "ContactCountPreview",
            "slug": "contact-count-preview",
            "queries": ["x"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    p = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=cid,
        google_place_id="ccp_1",
        name="Place 1",
        status="llm_done",
    )
    db_session.add(p)
    await db_session.flush()
    db_session.add(
        LeadgenLLMInsights(tenant_id="go4energy", place_id=p.id, target_match_score=8)
    )
    for i in range(3):
        db_session.add(
            LeadgenContact(
                tenant_id="go4energy",
                place_id=p.id,
                first_name=f"Person{i}",
                last_name="Test",
                full_name=f"Person{i} Test",
                source="managing_director",
            )
        )
    await db_session.commit()

    r = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich/preview",
        headers=HEADERS,
        json={"limit": 1, "stages": ["linkedin"]},
    )
    body = r.json()
    assert body["eligible_count"] == 1, "1 place matches"
    assert body["contact_count"] == 3, "3 contacts under that place"


@pytest.mark.anyio
async def test_linkedin_stage_filters_by_min_match_score(db_session, monkeypatch):
    """When state.min_match_score is set, the linkedin stage must only
    process places whose target_match_score >= the filter. Critical for
    "only run Serper on Top-7+ leads" budgeting.
    """
    from app.leadgen import worker as worker_mod
    from app.leadgen.models import LeadgenLLMInsights
    from app.leadgen.worker import _process_linkedin_stage

    campaign, run, places = await _build_linkedin_stage_fixture(db_session, 4)
    # Re-score the placed fixtures: 9, 7, 5, 3.
    insights = (
        await db_session.execute(
            select(LeadgenLLMInsights).where(
                LeadgenLLMInsights.place_id.in_([p.id for p in places])
            )
        )
    ).scalars().all()
    target_scores = {p.id: s for p, s in zip(places, [9, 7, 5, 3], strict=False)}
    for ins in insights:
        ins.target_match_score = target_scores[ins.place_id]
    run.stage_state = {"max_override": 10, "min_match_score": 7}
    await db_session.commit()

    async def _no_serper(*_a, **_kw):
        return None, 0.0

    monkeypatch.setattr(worker_mod, "find_company_linkedin_url", _no_serper)
    monkeypatch.setattr(worker_mod, "find_person_linkedin_url", _no_serper)
    monkeypatch.setattr(worker_mod.settings, "serper_api_key", "")

    class _NoLLM:
        async def generate_json(self, *a, **kw):
            return {}

    await _process_linkedin_stage(
        db_session,
        run=run,
        campaign=campaign,
        llm=_NoLLM(),
    )

    # Only the score=9 and score=7 places should be processed.
    state = run.stage_state or {}
    assert state.get("places_processed") == 2, state
    processed_ids = [
        p.id for p in places
        if (p.enrichment_flags or {}).get("linkedin_processed_at")
    ]
    assert processed_ids == [places[0].id, places[1].id]


@pytest.mark.anyio
async def test_linkedin_stage_skips_already_processed_places(db_session, monkeypatch):
    """Resumed run must not re-touch places stamped with
    enrichment_flags['linkedin_processed_at']. Crucial for cost — we must
    never burn Serper credits twice on the same place.
    """
    from app.leadgen import worker as worker_mod
    from app.leadgen.worker import _process_linkedin_stage

    campaign, run, places = await _build_linkedin_stage_fixture(db_session, 4)
    # Pre-stamp 2 places as already processed.
    for p in places[:2]:
        p.enrichment_flags = {"linkedin_processed_at": "2026-04-27T00:00:00"}
    run.stage_state = {"max_override": 4}
    await db_session.flush()

    serper_called = {"count": 0}

    async def _track_serper(*_a, **_kw):
        serper_called["count"] += 1
        return None, 0.0

    monkeypatch.setattr(worker_mod, "find_company_linkedin_url", _track_serper)
    monkeypatch.setattr(worker_mod, "find_person_linkedin_url", _track_serper)
    monkeypatch.setattr(worker_mod.settings, "serper_api_key", "fake-key")

    class _NoLLM:
        async def generate_json(self, *a, **kw):
            return {}

    await _process_linkedin_stage(
        db_session,
        run=run,
        campaign=campaign,
        llm=_NoLLM(),
    )

    # Only the 2 fresh places should have been processed this run.
    state = run.stage_state or {}
    assert state.get("places_processed") == 2, state

    # The 2 pre-stamped places must keep their old timestamp (no overwrite).
    for p in places[:2]:
        await db_session.refresh(p)
        assert (p.enrichment_flags or {}).get("linkedin_processed_at") == (
            "2026-04-27T00:00:00"
        )

    # Serper must have been called for the 2 fresh places' company URLs at most.
    # (No contacts materialised yet, so no per-contact calls expected.)
    assert serper_called["count"] <= 2


@pytest.mark.anyio
async def test_handoff_fills_tracking_hash_on_legacy_contact(client, db_session):
    """A Contact that exists but has no tracking_hash (created before the
    feature) should get a hash filled in on first handoff so the gap closes.
    """
    legacy = Contact(
        tenant_id="go4energy",
        name="Legacy GmbH",
        email="legacy-handoff@example.de",
        tracking_hash=None,
    )
    db_session.add(legacy)
    await db_session.commit()  # release the SQLite write lock before HTTP

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "HandoffLegacyTest",
            "slug": "handoff-legacy-test",
            "queries": ["dummy"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    place = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=cid,
        google_place_id="hh_test_legacy",
        name="Legacy GmbH",
        address_country="DE",
        status="llm_done",
    )
    db_session.add(place)
    await db_session.flush()
    db_session.add(
        LeadgenImpressum(
            tenant_id="go4energy",
            place_id=place.id,
            email="legacy-handoff@example.de",
            managing_directors=["A B"],
        )
    )
    db_session.add(
        LeadgenLLMInsights(
            tenant_id="go4energy",
            place_id=place.id,
            target_match_score=9,
        )
    )
    await db_session.commit()

    h = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/handoff",
        headers=HEADERS,
        json={"min_score": 0, "limit": 10},
    )
    assert h.status_code == 200, h.text

    # The HTTP request committed via its own session; expire the test
    # session's identity map so the next SELECT reads from disk and not
    # from the cached pre-handoff snapshot of ``legacy``.
    db_session.expire_all()
    refreshed = (
        await db_session.execute(
            select(Contact).where(Contact.email == "legacy-handoff@example.de")
        )
    ).scalar_one()
    assert refreshed.tracking_hash, "handoff must fill missing hash on reused contact"
    assert re.fullmatch(r"[A-Za-z0-9]{12}", refreshed.tracking_hash)
