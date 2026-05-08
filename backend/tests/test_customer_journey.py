"""Customer Journey module tests - identify, events, ref-codes, campaigns."""

import pytest
import pytest_asyncio

from tests.conftest import TEST_AUTH_HEADERS

# Tracking API uses settings.default_tenant_id, so internal endpoints must match
TENANT_HEADERS = {**TEST_AUTH_HEADERS, "X-Tenant-ID": "go4energy"}


@pytest_asyncio.fixture
async def tenant(client):
    """Ensure go4energy tenant exists (tracking API uses default_tenant_id)."""
    response = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "go4energy", "tenant_name": "go4energy"},
    )
    assert response.status_code in (201, 409)
    return "go4energy"


@pytest_asyncio.fixture
async def api_key_headers():
    """Headers for external tracking API (single-key legacy path)."""
    from app.config import settings

    settings.tracking_api_key = "test-tracking-key"
    settings.tracking_api_keys = {}  # force legacy fallback
    return {"Authorization": "Bearer test-tracking-key"}


@pytest_asyncio.fixture
async def multi_key_headers():
    """Configure two source-labelled keys; return go4 + smartladen header sets."""
    from app.config import settings

    settings.tracking_api_key = ""
    settings.tracking_api_keys = {
        "go4.energy": "key-go4",
        "smartladen.de": "key-sl",
    }
    return {
        "go4": {"Authorization": "Bearer key-go4"},
        "smartladen": {"Authorization": "Bearer key-sl"},
    }


# ============== Identify ==============


@pytest.mark.anyio
async def test_identify_creates_new_lead(client, tenant, api_key_headers):
    """Identify with new email should create a lead."""
    response = await client.post(
        "/api/v1/tracking/identify",
        json={
            "name": "Max Mustermann",
            "email": "max@example.com",
            "phone": "+491701234567",
            "source": "konfigurator",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["is_new"] is True
    assert len(data["tracking_hash"]) == 12
    assert data["lead_id"] > 0


@pytest.mark.anyio
async def test_identify_finds_existing_lead(client, tenant, api_key_headers):
    """Identify with existing email should return same lead."""
    # Create
    r1 = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "repeat@example.com", "name": "Test"},
        headers=api_key_headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()

    # Find
    r2 = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "repeat@example.com", "source": "second_visit"},
        headers=api_key_headers,
    )
    assert r2.status_code == 200
    d2 = r2.json()

    assert d2["is_new"] is False
    assert d2["lead_id"] == d1["lead_id"]
    assert d2["tracking_hash"] == d1["tracking_hash"]


@pytest.mark.anyio
async def test_identify_rejects_bad_api_key(client, tenant):
    """Identify with wrong API key should return 401."""
    response = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "test@example.com", "name": "Test"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


# ============== Events ==============


@pytest.mark.anyio
async def test_track_event_with_hash(client, tenant, api_key_headers):
    """Track event with valid tracking_hash should succeed."""
    # Create lead
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "event-test@example.com", "name": "Event Test"},
        headers=api_key_headers,
    )
    tracking_hash = r.json()["tracking_hash"]

    # Track event
    response = await client.post(
        "/api/v1/tracking/event",
        json={
            "tracking_hash": tracking_hash,
            "event": "page_visit",
            "page_path": "/photovoltaik/konfigurator",
            "utm_source": "google",
            "source_site": "go4.energy",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["tracking_hash"] == tracking_hash


@pytest.mark.anyio
async def test_track_event_unknown_hash_returns_null(client, tenant, api_key_headers):
    """Track event with unknown hash should return null tracking_hash."""
    response = await client.post(
        "/api/v1/tracking/event",
        json={
            "tracking_hash": "nonexistent99",
            "event": "page_visit",
            "page_path": "/test",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["tracking_hash"] is None


@pytest.mark.anyio
async def test_batch_events(client, tenant, api_key_headers):
    """Batch events should process multiple events."""
    # Create lead
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "batch@example.com", "name": "Batch Test"},
        headers=api_key_headers,
    )
    h = r.json()["tracking_hash"]

    response = await client.post(
        "/api/v1/tracking/event/batch",
        json={
            "events": [
                {"tracking_hash": h, "event": "page_visit", "page_path": "/a"},
                {"tracking_hash": h, "event": "konfigurator_start"},
                {"tracking_hash": h, "event": "konfigurator_complete"},
            ]
        },
        headers=api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["processed"] == 3
    assert data["errors"] == 0


# ============== Ref-Code Resolution ==============


@pytest.mark.anyio
async def test_resolve_ref_code(client, tenant, api_key_headers):
    """Resolve a ref-code should return tracking hash."""
    # Create lead
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "ref-test@example.com", "name": "Ref Test"},
        headers=api_key_headers,
    )
    contact_id = r.json()["lead_id"]
    tracking_hash = r.json()["tracking_hash"]

    # Create ref-code
    ref_r = await client.post(
        "/api/v1/customer-journey/refs",
        json={"name": "Test Ref", "contact_id": contact_id, "ref_code": "TESTREF"},
        headers=TENANT_HEADERS,
    )
    assert ref_r.status_code == 201

    # Resolve
    response = await client.get(
        "/api/v1/tracking/ref/TESTREF",
        headers=api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["tracking_hash"] == tracking_hash
    assert data["lead_name"] == "Ref Test"


@pytest.mark.anyio
async def test_resolve_unknown_ref_returns_404(client, tenant, api_key_headers):
    """Resolve unknown ref-code should return 404."""
    response = await client.get(
        "/api/v1/tracking/ref/NOPE123",
        headers=api_key_headers,
    )
    assert response.status_code == 404


# ============== Dashboard ==============


@pytest.mark.anyio
async def test_dashboard_stats(client, tenant, api_key_headers):
    """Dashboard stats should return counts."""
    # Create a lead first
    await client.post(
        "/api/v1/tracking/identify",
        json={"email": "dash@example.com", "name": "Dashboard Test"},
        headers=api_key_headers,
    )

    response = await client.get(
        "/api/v1/customer-journey/dashboard/stats",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["leads_total"] >= 1
    assert data["events_today"] >= 0


@pytest.mark.anyio
async def test_dashboard_feed(client, tenant):
    """Dashboard feed should return events list."""
    response = await client.get(
        "/api/v1/customer-journey/dashboard/feed",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_dashboard_feed_days_since_last_visit(client, tenant, api_key_headers):
    """Feed should show days_since_last_visit for returning visitors."""
    from datetime import datetime, timedelta

    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyEvent
    from tests.conftest import test_session_factory

    now = datetime.utcnow()

    # Create contact + events directly in the DB so we control timestamps
    session = test_session_factory()
    try:
        contact = Contact(
            tenant_id="go4energy",
            name="Return Visitor",
            email="return-visitor@example.com",
            tracking_hash="rvTestHash01",
            journey_status="active",
        )
        session.add(contact)
        session.flush()

        old_event = JourneyEvent(
            tenant_id="go4energy",
            contact_id=contact.id,
            event="page_visit",
            category="awareness",
            page_path="/old-page",
            source_site="go4.energy",
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        new_event = JourneyEvent(
            tenant_id="go4energy",
            contact_id=contact.id,
            event="page_visit",
            category="awareness",
            page_path="/new-page",
            source_site="go4.energy",
            created_at=now,
            updated_at=now,
        )
        session.add_all([old_event, new_event])
        session.commit()
    finally:
        session.close()

    # Fetch feed and check days_since_last_visit
    response = await client.get(
        "/api/v1/customer-journey/dashboard/feed",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    feed = response.json()

    # Find events for our return visitor
    visitor_events = [e for e in feed if e.get("contact_email") == "return-visitor@example.com"]
    assert len(visitor_events) == 2

    # The most recent event should have days_since_last_visit >= 4
    newest = visitor_events[0]
    assert newest["days_since_last_visit"] is not None
    assert newest["days_since_last_visit"] >= 4

    # The oldest event (first ever for this contact) should have no gap
    oldest = visitor_events[-1]
    assert oldest["days_since_last_visit"] is None


# ============== Dashboard Feed By Lead ==============


@pytest.mark.anyio
async def test_dashboard_feed_by_lead_groups_events(client, tenant, api_key_headers):
    """Feed-by-lead returns leads with their recent events grouped."""
    from datetime import datetime, timedelta

    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyEvent
    from tests.conftest import test_session_factory

    now = datetime.utcnow()

    session = test_session_factory()
    try:
        # Lead A — most recent event (newest)
        lead_a = Contact(
            tenant_id="go4energy",
            name="Lead A",
            email="lead-a@example.com",
            tracking_hash="leadAHash01",
            journey_status="active",
        )
        # Lead B — older last event
        lead_b = Contact(
            tenant_id="go4energy",
            name="Lead B",
            email="lead-b@example.com",
            tracking_hash="leadBHash01",
            journey_status="active",
        )
        session.add_all([lead_a, lead_b])
        session.flush()

        events = [
            JourneyEvent(
                tenant_id="go4energy",
                contact_id=lead_a.id,
                event="page_visit",
                category="awareness",
                page_path="/a-old",
                source_site="go4.energy",
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
            ),
            JourneyEvent(
                tenant_id="go4energy",
                contact_id=lead_a.id,
                event="konfigurator_complete",
                category="conversion",
                page_path="/a-new",
                source_site="go4.energy",
                created_at=now - timedelta(minutes=5),
                updated_at=now - timedelta(minutes=5),
            ),
            JourneyEvent(
                tenant_id="go4energy",
                contact_id=lead_b.id,
                event="page_visit",
                category="awareness",
                page_path="/b",
                source_site="go4.energy",
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            ),
        ]
        session.add_all(events)
        session.commit()
    finally:
        session.close()

    response = await client.get(
        "/api/v1/customer-journey/dashboard/feed-by-lead",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    feed = response.json()

    # Lead A must come before Lead B (newer last_event_at)
    a_idx = next(i for i, r in enumerate(feed) if r["email"] == "lead-a@example.com")
    b_idx = next(i for i, r in enumerate(feed) if r["email"] == "lead-b@example.com")
    assert a_idx < b_idx

    lead_a_row = feed[a_idx]
    assert lead_a_row["event_count"] == 2
    assert len(lead_a_row["events"]) == 2
    # Events must be newest first within the lead
    assert lead_a_row["events"][0]["event"] == "konfigurator_complete"
    assert lead_a_row["events"][1]["event"] == "page_visit"

    lead_b_row = feed[b_idx]
    assert lead_b_row["event_count"] == 1
    assert len(lead_b_row["events"]) == 1


@pytest.mark.anyio
async def test_dashboard_feed_by_lead_respects_events_per_lead(
    client, tenant, api_key_headers
):
    """events_per_lead limits inline events without changing total count."""
    from datetime import datetime, timedelta

    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyEvent
    from tests.conftest import test_session_factory

    now = datetime.utcnow()
    session = test_session_factory()
    try:
        contact = Contact(
            tenant_id="go4energy",
            name="Many Events",
            email="many-events@example.com",
            tracking_hash="manyEvHash01",
            journey_status="active",
        )
        session.add(contact)
        session.flush()
        for i in range(15):
            session.add(
                JourneyEvent(
                    tenant_id="go4energy",
                    contact_id=contact.id,
                    event=f"page_visit_{i}",
                    category="awareness",
                    source_site="go4.energy",
                    created_at=now - timedelta(minutes=i),
                    updated_at=now - timedelta(minutes=i),
                )
            )
        session.commit()
    finally:
        session.close()

    response = await client.get(
        "/api/v1/customer-journey/dashboard/feed-by-lead",
        params={"events_per_lead": 5},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    rows = response.json()
    target = next(r for r in rows if r["email"] == "many-events@example.com")
    assert target["event_count"] == 15
    assert len(target["events"]) == 5
    # Newest first
    assert target["events"][0]["event"] == "page_visit_0"


@pytest.mark.anyio
async def test_dashboard_feed_by_lead_search_filter(client, tenant, api_key_headers):
    """Search filter narrows leads by name/email."""
    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyEvent
    from tests.conftest import test_session_factory

    session = test_session_factory()
    try:
        for name, email in [("Alice", "alice@example.com"), ("Bob", "bob@example.com")]:
            c = Contact(
                tenant_id="go4energy",
                name=name,
                email=email,
                tracking_hash=f"search{name}",
                journey_status="active",
            )
            session.add(c)
            session.flush()
            session.add(
                JourneyEvent(
                    tenant_id="go4energy",
                    contact_id=c.id,
                    event="page_visit",
                    category="awareness",
                    source_site="go4.energy",
                )
            )
        session.commit()
    finally:
        session.close()

    response = await client.get(
        "/api/v1/customer-journey/dashboard/feed-by-lead",
        params={"search": "alice"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    rows = response.json()
    assert all("alice" in r["email"].lower() or "alice" in r["name"].lower() for r in rows)
    assert any(r["email"] == "alice@example.com" for r in rows)


# ============== Leads List ==============


@pytest.mark.anyio
async def test_list_leads(client, tenant, api_key_headers):
    """List leads should return contacts with tracking_hash."""
    # Create a lead
    await client.post(
        "/api/v1/tracking/identify",
        json={"email": "list-test@example.com", "name": "List Lead"},
        headers=api_key_headers,
    )

    response = await client.get(
        "/api/v1/customer-journey/leads",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    lead = data[0]
    assert "tracking_hash" in lead
    assert "event_count" in lead


# ============== Timeline ==============


@pytest.mark.anyio
async def test_lead_timeline(client, tenant, api_key_headers):
    """Lead timeline should return journey events."""
    # Create lead with events
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "timeline@example.com", "name": "Timeline Test"},
        headers=api_key_headers,
    )
    contact_id = r.json()["lead_id"]
    tracking_hash = r.json()["tracking_hash"]

    # Add events
    await client.post(
        "/api/v1/tracking/event",
        json={"tracking_hash": tracking_hash, "event": "page_visit", "page_path": "/test"},
        headers=api_key_headers,
    )

    response = await client.get(
        f"/api/v1/customer-journey/leads/{contact_id}/timeline",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["event"] in ("page_visit", "identify")


# ============== Ref-Code CRUD ==============


@pytest.mark.anyio
async def test_create_ref_code(client, tenant):
    """Create ref-code should return 201."""
    response = await client.post(
        "/api/v1/customer-journey/refs",
        json={"name": "Test Person", "context": "Newsletter März"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["ref_code"]) == 6
    assert data["name"] == "Test Person"


@pytest.mark.anyio
async def test_bulk_create_ref_codes(client, tenant):
    """Bulk create ref-codes from text lines."""
    response = await client.post(
        "/api/v1/customer-journey/refs/bulk",
        json={"lines": "Person A;Kontext A\nPerson B;Kontext B\nPerson C"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "Person A"
    assert data[0]["context"] == "Kontext A"
    assert data[2]["context"] is None


@pytest.mark.anyio
async def test_list_ref_codes(client, tenant):
    """List ref-codes should return array."""
    # Create one first
    await client.post(
        "/api/v1/customer-journey/refs",
        json={"name": "Lister"},
        headers=TENANT_HEADERS,
    )

    response = await client.get(
        "/api/v1/customer-journey/refs",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.anyio
async def test_update_ref_code(client, tenant):
    """Update ref-code should change fields."""
    # Create
    r = await client.post(
        "/api/v1/customer-journey/refs",
        json={"name": "Original"},
        headers=TENANT_HEADERS,
    )
    ref_id = r.json()["id"]

    # Update
    response = await client.put(
        f"/api/v1/customer-journey/refs/{ref_id}",
        json={"name": "Updated", "context": "New Context"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert response.json()["context"] == "New Context"


@pytest.mark.anyio
async def test_delete_ref_code(client, tenant):
    """Delete ref-code should return 204."""
    r = await client.post(
        "/api/v1/customer-journey/refs",
        json={"name": "To Delete"},
        headers=TENANT_HEADERS,
    )
    ref_id = r.json()["id"]

    response = await client.delete(
        f"/api/v1/customer-journey/refs/{ref_id}",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 204


# ============== ensure_ref_code (idempotent helper) ==============


@pytest.mark.anyio
async def test_ensure_ref_code_idempotent(client, tenant, db_session):
    """ensure_ref_code returns the same code on repeat calls for the
    same (contact, campaign) — no duplicates created."""
    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyCampaign
    from app.customer_journey.service import RefCodeService

    contact = Contact(
        tenant_id=tenant,
        email="ensure-test@example.com",
        name="Ensure Test",
        tracking_hash="abc123def456",
    )
    db_session.add(contact)
    await db_session.flush()

    campaign = JourneyCampaign(
        tenant_id=tenant, name="Ensure Test Campaign", channel="email"
    )
    db_session.add(campaign)
    await db_session.flush()

    svc = RefCodeService(db_session)

    ref1 = await svc.ensure_ref_code(
        tenant_id=tenant,
        contact=contact,
        campaign=campaign,
        target_url="https://go4.energy",
        utm_source="outreach",
    )
    ref2 = await svc.ensure_ref_code(
        tenant_id=tenant,
        contact=contact,
        campaign=campaign,
        target_url="https://go4.energy",
        utm_source="outreach",
    )

    assert ref1.id == ref2.id
    assert ref1.ref_code == ref2.ref_code
    assert len(ref1.ref_code) == 6
    assert ref1.contact_id == contact.id
    assert ref1.campaign_id == campaign.id


@pytest.mark.anyio
async def test_ensure_ref_code_distinct_per_campaign(client, tenant, db_session):
    """Same contact, two different campaigns → two distinct ref-codes."""
    from app.contacts.models import Contact
    from app.customer_journey.models import JourneyCampaign
    from app.customer_journey.service import RefCodeService

    contact = Contact(
        tenant_id=tenant,
        email="multicamp@example.com",
        name="Multi Campaign",
        tracking_hash="multicamp1234",
    )
    db_session.add(contact)
    await db_session.flush()

    camp_a = JourneyCampaign(
        tenant_id=tenant, name="Cold Mail", channel="email"
    )
    camp_b = JourneyCampaign(
        tenant_id=tenant, name="WhatsApp Q3", channel="whatsapp"
    )
    db_session.add_all([camp_a, camp_b])
    await db_session.flush()

    svc = RefCodeService(db_session)
    ref_a = await svc.ensure_ref_code(
        tenant_id=tenant, contact=contact, campaign=camp_a
    )
    ref_b = await svc.ensure_ref_code(
        tenant_id=tenant, contact=contact, campaign=camp_b
    )

    assert ref_a.id != ref_b.id
    assert ref_a.ref_code != ref_b.ref_code
    assert ref_a.campaign_id == camp_a.id
    assert ref_b.campaign_id == camp_b.id


# ============== Campaign CRUD ==============


@pytest.mark.anyio
async def test_create_campaign(client, tenant):
    """Create campaign should return 201."""
    response = await client.post(
        "/api/v1/customer-journey/campaigns",
        json={"name": "LinkedIn März 2026", "channel": "linkedin"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "LinkedIn März 2026"
    assert data["channel"] == "linkedin"
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_list_campaigns(client, tenant):
    """List campaigns should return array."""
    await client.post(
        "/api/v1/customer-journey/campaigns",
        json={"name": "Test Campaign"},
        headers=TENANT_HEADERS,
    )

    response = await client.get(
        "/api/v1/customer-journey/campaigns",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.anyio
async def test_update_campaign(client, tenant):
    """Update campaign should change fields."""
    r = await client.post(
        "/api/v1/customer-journey/campaigns",
        json={"name": "Original Campaign"},
        headers=TENANT_HEADERS,
    )
    cid = r.json()["id"]

    response = await client.put(
        f"/api/v1/customer-journey/campaigns/{cid}",
        json={"name": "Renamed Campaign", "status": "paused"},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Campaign"
    assert response.json()["status"] == "paused"


@pytest.mark.anyio
async def test_delete_campaign(client, tenant):
    """Delete campaign should return 204."""
    r = await client.post(
        "/api/v1/customer-journey/campaigns",
        json={"name": "To Delete"},
        headers=TENANT_HEADERS,
    )
    cid = r.json()["id"]

    response = await client.delete(
        f"/api/v1/customer-journey/campaigns/{cid}",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 204


# ============== CSV Import ==============

CSV_SAMPLE = (
    "full_name;job_position;profile_linkedin;company;location\n"
    "Max Mustermann;CTO;https://linkedin.com/in/max;ACME Corp;Berlin\n"
    "Erika Muster;CEO;https://linkedin.com/in/erika;Test GmbH;München\n"
)

IMPORT_MAPPING = {
    "full_name": "name",
    "job_position": "position",
    "profile_linkedin": "linkedin",
    "company": "custom:company",
    "location": "custom:location",
}


@pytest.mark.anyio
async def test_import_get_fields(client, tenant):
    """Should return list of mappable fields."""
    response = await client.get(
        "/api/v1/customer-journey/import/fields",
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    fields = response.json()
    assert len(fields) > 0
    keys = [f["key"] for f in fields]
    assert "name" in keys
    assert "linkedin" in keys


@pytest.mark.anyio
async def test_import_preview(client, tenant):
    """Preview should detect new rows and no conflicts for fresh data."""
    response = await client.post(
        "/api/v1/customer-journey/import/preview",
        json={"csv_raw": CSV_SAMPLE, "mapping": IMPORT_MAPPING},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] == 2
    assert data["new_count"] == 2
    assert data["conflict_count"] == 0


@pytest.mark.anyio
async def test_import_preview_detects_conflict(client, tenant):
    """Preview should detect conflict when linkedin URL already exists."""
    from app.contacts.models import Contact
    from tests.conftest import test_session_factory

    # Pre-create contact with matching linkedin
    session = test_session_factory()
    try:
        c = Contact(
            tenant_id="go4energy",
            name="Existing Max",
            email="existing@example.com",
            linkedin="https://linkedin.com/in/max",
        )
        session.add(c)
        session.commit()
    finally:
        session.close()

    response = await client.post(
        "/api/v1/customer-journey/import/preview",
        json={"csv_raw": CSV_SAMPLE, "mapping": IMPORT_MAPPING},
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["conflict_count"] == 1
    assert data["new_count"] == 1
    assert data["conflicts"][0]["existing_contact"]["name"] == "Existing Max"


@pytest.mark.anyio
async def test_import_execute(client, tenant):
    """Execute should create contacts, ref-codes and return CSV with ref_link."""
    response = await client.post(
        "/api/v1/customer-journey/import/execute",
        json={
            "csv_raw": CSV_SAMPLE,
            "mapping": IMPORT_MAPPING,
            "base_url": "https://go4.energy/angebot",
            "campaign_id": None,
            "conflict_resolutions": {},
        },
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    # Response is CSV
    csv_text = response.text
    lines = csv_text.strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    assert "ref_link" in lines[0]
    # Each row should have a ref link
    assert "ref=" in lines[1]
    assert "ref=" in lines[2]
    assert "https://go4.energy/angebot?ref=" in lines[1]


@pytest.mark.anyio
async def test_import_execute_skip_conflict(client, tenant):
    """Execute should skip conflicting rows when resolution is 'skip'."""
    from app.contacts.models import Contact
    from tests.conftest import test_session_factory

    # Pre-create contact with matching linkedin
    session = test_session_factory()
    try:
        c = Contact(
            tenant_id="go4energy",
            name="Skip Max",
            email="skip@example.com",
            linkedin="https://linkedin.com/in/max",
        )
        session.add(c)
        session.commit()
    finally:
        session.close()

    response = await client.post(
        "/api/v1/customer-journey/import/execute",
        json={
            "csv_raw": CSV_SAMPLE,
            "mapping": IMPORT_MAPPING,
            "base_url": "https://go4.energy/test",
            "campaign_id": None,
            "conflict_resolutions": {"0": "skip"},
        },
        headers=TENANT_HEADERS,
    )
    assert response.status_code == 200
    csv_text = response.text
    lines = csv_text.strip().split("\n")
    # Row 0 (Max) was skipped → no ref_link, Row 1 (Erika) has ref_link
    assert lines[1].endswith(";") or "ref=" not in lines[1]  # skipped
    assert "ref=" in lines[2]  # created


# ============== Multi-Key Auth + source_site stamping ==============


@pytest.mark.anyio
async def test_multi_key_accepts_both(client, tenant, multi_key_headers):
    """Both configured keys should be accepted."""
    for key_set in (multi_key_headers["go4"], multi_key_headers["smartladen"]):
        r = await client.post(
            "/api/v1/tracking/identify",
            json={"email": f"u-{key_set['Authorization'][-3:]}@example.com",
                  "name": "U"},
            headers=key_set,
        )
        assert r.status_code == 200


@pytest.mark.anyio
async def test_multi_key_rejects_unknown(client, tenant, multi_key_headers):
    """Unknown bearer token must be rejected when multi-key map is set."""
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "x@example.com", "name": "X"},
        headers={"Authorization": "Bearer not-a-real-key"},
    )
    assert r.status_code == 401


@pytest.mark.anyio
async def test_event_source_site_from_key(
    client, tenant, multi_key_headers, db_session
):
    """source_site of stored event must come from the API key, not the payload."""
    from sqlalchemy import select

    from app.customer_journey.models import JourneyEvent

    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "src@example.com", "name": "Src"},
        headers=multi_key_headers["smartladen"],
    )
    h = r.json()["tracking_hash"]

    # Try to spoof source_site via payload — must be ignored
    await client.post(
        "/api/v1/tracking/event",
        json={
            "tracking_hash": h,
            "event": "page_visit",
            "page_path": "/x",
            "source_site": "evil.com",
        },
        headers=multi_key_headers["smartladen"],
    )

    rows = (
        await db_session.execute(
            select(JourneyEvent.source_site)
            .where(JourneyEvent.event == "page_visit")
            .order_by(JourneyEvent.id.desc())
        )
    ).scalars().all()
    assert rows
    assert rows[0] == "smartladen.de"


@pytest.mark.anyio
async def test_dashboard_feed_source_filter(
    client, tenant, multi_key_headers,
):
    """Live-Feed should respect ?source_site filter."""
    # Two events from different sources via different keys
    for label, hdr_key, email in (
        ("go4", "go4", "feed-go4@example.com"),
        ("sl", "smartladen", "feed-sl@example.com"),
    ):
        r = await client.post(
            "/api/v1/tracking/identify",
            json={"email": email, "name": label},
            headers=multi_key_headers[hdr_key],
        )
        h = r.json()["tracking_hash"]
        await client.post(
            "/api/v1/tracking/event",
            json={"tracking_hash": h, "event": "page_visit", "page_path": "/"},
            headers=multi_key_headers[hdr_key],
        )

    # Unfiltered — both sources visible
    r_all = await client.get(
        "/api/v1/customer-journey/dashboard/feed",
        headers=TENANT_HEADERS,
    )
    assert r_all.status_code == 200
    sources = {e["source_site"] for e in r_all.json()}
    assert "go4.energy" in sources
    assert "smartladen.de" in sources

    # Filtered to smartladen
    r_sl = await client.get(
        "/api/v1/customer-journey/dashboard/feed",
        params={"source_site": "smartladen.de"},
        headers=TENANT_HEADERS,
    )
    assert r_sl.status_code == 200
    assert all(e["source_site"] == "smartladen.de" for e in r_sl.json())
    assert any(e["source_site"] == "smartladen.de" for e in r_sl.json())


@pytest.mark.anyio
async def test_dashboard_sources_endpoint(
    client, tenant, multi_key_headers,
):
    """Sources endpoint should list distinct source_site values."""
    # Seed one event per source
    for hdr_key, email in (("go4", "s-go4@example.com"), ("smartladen", "s-sl@example.com")):
        r = await client.post(
            "/api/v1/tracking/identify",
            json={"email": email, "name": "x"},
            headers=multi_key_headers[hdr_key],
        )
        h = r.json()["tracking_hash"]
        await client.post(
            "/api/v1/tracking/event",
            json={"tracking_hash": h, "event": "page_visit", "page_path": "/"},
            headers=multi_key_headers[hdr_key],
        )

    r = await client.get(
        "/api/v1/customer-journey/dashboard/sources",
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert "go4.energy" in body
    assert "smartladen.de" in body


# ============== IP Blocklist ==============


@pytest_asyncio.fixture
async def blocked_ip_setting():
    """Configure 198.51.100.42 as blocked, restore after test."""
    from app.config import settings

    original = settings.tracking_blocked_ips
    settings.tracking_blocked_ips = ["198.51.100.42"]
    try:
        yield "198.51.100.42"
    finally:
        settings.tracking_blocked_ips = original


@pytest.mark.anyio
async def test_identify_blocked_ip_returns_sentinel(
    client, tenant, api_key_headers, blocked_ip_setting,
):
    """Identify from blocked IP should return sentinel without creating contact."""
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "blocked-id@example.com", "name": "Blocked"},
        headers={**api_key_headers, "x-forwarded-for": blocked_ip_setting},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["lead_id"] == 0
    assert body["tracking_hash"] == ""
    assert body["is_new"] is False


@pytest.mark.anyio
async def test_event_blocked_ip_returns_null(
    client, tenant, api_key_headers, blocked_ip_setting,
):
    """Event from blocked IP should return null tracking_hash."""
    # Allowed identify first to have a hash
    r = await client.post(
        "/api/v1/tracking/identify",
        json={"email": "ev-blocked@example.com", "name": "Ev"},
        headers=api_key_headers,
    )
    h = r.json()["tracking_hash"]

    r2 = await client.post(
        "/api/v1/tracking/event",
        json={"tracking_hash": h, "event": "page_visit", "page_path": "/"},
        headers={**api_key_headers, "x-forwarded-for": blocked_ip_setting},
    )
    assert r2.status_code == 200
    assert r2.json()["tracking_hash"] is None


@pytest.mark.anyio
async def test_batch_blocked_ip_processes_zero(
    client, tenant, api_key_headers, blocked_ip_setting,
):
    """Batch from blocked IP should process zero events."""
    r = await client.post(
        "/api/v1/tracking/event/batch",
        json={"events": [
            {"tracking_hash": "abc", "event": "page_visit", "page_path": "/"},
        ]},
        headers={**api_key_headers, "x-forwarded-for": blocked_ip_setting},
    )
    assert r.status_code == 200
    assert r.json()["processed"] == 0


@pytest.mark.anyio
async def test_prepare_link_ignores_blocked_ip(
    client, tenant, api_key_headers, blocked_ip_setting,
):
    """Prepare-link is server-to-server (Odoo) and must NOT be IP-blocked,
    even when the caller's IP is on TRACKING_BLOCKED_IPS — the blocklist
    targets browser-driven endpoints only."""
    r = await client.post(
        "/api/v1/tracking/prepare-link",
        json={"email": "pl-allowed@example.com", "name": "PL"},
        headers={**api_key_headers, "x-forwarded-for": blocked_ip_setting},
    )
    assert r.status_code == 200
    body = r.json()
    # Real ref-code created (not the sentinel "")
    assert body["contact_id"] > 0
    assert body["ref_code"] != ""
    assert body["link"] != ""


@pytest.mark.anyio
async def test_prepare_link_is_idempotent_for_same_contact_and_campaign(
    client, tenant, api_key_headers,
):
    """Repeating prepare-link for the same (email, campaign_name) must return
    the existing ref-code instead of attempting a second INSERT.

    The DB enforces a partial-unique index on (contact_id, campaign_id) where
    both are NOT NULL (Migration 085). Without idempotent lookup, the second
    call raises UniqueViolation → 500 (regression seen 2026-05-05 with
    smartladen.de mass-mailing)."""
    payload = {
        "email": "idempotent@example.com",
        "name": "Idempotent",
        "campaign_name": "Re-Send Test",
        "target_url": "https://demo.smartladen.de/demo-login",
        "utm_source": "smartladen-demo",
    }
    r1 = await client.post(
        "/api/v1/tracking/prepare-link", json=payload, headers=api_key_headers,
    )
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["is_new_ref"] is True
    assert body1["ref_code"] != ""

    r2 = await client.post(
        "/api/v1/tracking/prepare-link", json=payload, headers=api_key_headers,
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["is_new_ref"] is False
    assert body2["ref_code"] == body1["ref_code"]
    assert body2["contact_id"] == body1["contact_id"]
