"""Tests for the leadgen module."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.leadgen.places_client import _parse_place

HEADERS = {"X-Tenant-ID": "go4energy"}


# ---------------- Places Client parsing ----------------


def test_parse_place_full_payload():
    """Full Places API response should be parsed into structured fields."""
    payload = {
        "id": "ChIJabc123",
        "displayName": {"text": "Elektro Mueller GmbH", "languageCode": "de"},
        "formattedAddress": "Hauptstr. 42, 10115 Berlin, Deutschland",
        "addressComponents": [
            {"longText": "42", "shortText": "42", "types": ["street_number"]},
            {"longText": "Hauptstraße", "shortText": "Hauptstr.", "types": ["route"]},
            {"longText": "10115", "shortText": "10115", "types": ["postal_code"]},
            {"longText": "Berlin", "shortText": "Berlin", "types": ["locality"]},
            {"longText": "Deutschland", "shortText": "DE", "types": ["country"]},
        ],
        "location": {"latitude": 52.523, "longitude": 13.411},
        "websiteUri": "https://elektro-mueller.example.de",
        "nationalPhoneNumber": "+49 30 12345678",
        "types": ["electrician", "point_of_interest"],
        "rating": 4.6,
        "userRatingCount": 87,
        "businessStatus": "OPERATIONAL",
    }
    p = _parse_place(payload)
    assert p.google_place_id == "ChIJabc123"
    assert p.name == "Elektro Mueller GmbH"
    assert p.address_street == "Hauptstraße 42"
    assert p.address_zip == "10115"
    assert p.address_city == "Berlin"
    assert p.address_country == "DE"
    assert p.lat == 52.523
    assert p.lng == 13.411
    assert p.website == "https://elektro-mueller.example.de"
    assert p.phone == "+49 30 12345678"
    assert p.google_categories == ["electrician", "point_of_interest"]
    assert p.rating == 4.6
    assert p.user_ratings_total == 87
    assert p.business_status == "OPERATIONAL"
    assert p.raw_payload == payload


def test_parse_place_minimal_payload():
    """Missing optional fields must not raise."""
    payload = {"id": "ChIJmin", "displayName": {"text": "Minimal Firma"}}
    p = _parse_place(payload)
    assert p.google_place_id == "ChIJmin"
    assert p.name == "Minimal Firma"
    assert p.address_street is None
    assert p.website is None
    assert p.google_categories == []


def test_parse_place_handles_missing_name():
    """Empty displayName should not crash."""
    p = _parse_place({"id": "ChIJempty", "displayName": {"text": ""}})
    assert p.name == "(ohne Namen)"


# ---------------- Campaign CRUD ----------------


@pytest.mark.anyio
async def test_leadgen_health(client):
    resp = await client.get("/api/v1/leadgen/health", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"module": "leadgen", "healthy": True}


@pytest.mark.anyio
async def test_create_campaign_without_pipeline(client):
    """Campaign with no pipeline is allowed; run-start will fail later."""
    resp = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "PV Elektro DE",
            "slug": "pv-elektro-de",
            "queries": ["Elektriker Berlin"],
            "language": "de",
            "region": "DE",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "pv-elektro-de"
    assert data["status"] == "draft"
    assert data["target_engagement_pipeline_id"] is None


@pytest.mark.anyio
async def test_create_campaign_with_auto_pipeline(client):
    resp = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "Solar Elektro",
            "slug": "solar-elektro",
            "queries": ["Elektroinstallation Hamburg"],
            "create_new_pipeline": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["target_engagement_pipeline_id"] is not None

    # Verify the pipeline exists in engagement
    pid = data["target_engagement_pipeline_id"]
    pipe_resp = await client.get(
        f"/api/v1/engagement/pipelines/{pid}", headers=HEADERS
    )
    assert pipe_resp.status_code == 200
    pipe = pipe_resp.json()
    assert pipe["slug"].startswith("leadgen-solar-elektro")
    assert "postmail" in pipe["channels"]
    assert "email" in pipe["channels"]


@pytest.mark.anyio
async def test_duplicate_campaign_slug_rejected(client):
    base = {"name": "A", "slug": "dup-slug", "queries": ["x"]}
    r1 = await client.post("/api/v1/leadgen/campaigns", headers=HEADERS, json=base)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/leadgen/campaigns", headers=HEADERS, json=base)
    assert r2.status_code == 409


@pytest.mark.anyio
async def test_campaign_crud_cycle(client):
    # create
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={"name": "CRUD", "slug": "crud-cycle", "queries": ["a"]},
    )
    assert r.status_code == 201
    cid = r.json()["id"]

    # get
    r = await client.get(f"/api/v1/leadgen/campaigns/{cid}", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["name"] == "CRUD"

    # list
    r = await client.get("/api/v1/leadgen/campaigns", headers=HEADERS)
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    # update
    r = await client.put(
        f"/api/v1/leadgen/campaigns/{cid}",
        headers=HEADERS,
        json={"name": "CRUD Updated", "status": "paused"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "CRUD Updated"
    assert r.json()["status"] == "paused"

    # delete
    r = await client.delete(f"/api/v1/leadgen/campaigns/{cid}", headers=HEADERS)
    assert r.status_code == 204

    # gone
    r = await client.get(f"/api/v1/leadgen/campaigns/{cid}", headers=HEADERS)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_stats_empty_campaign(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={"name": "Stats", "slug": "stats-test", "queries": ["q"]},
    )
    cid = r.json()["id"]
    s = await client.get(
        f"/api/v1/leadgen/campaigns/{cid}/stats", headers=HEADERS
    )
    assert s.status_code == 200
    data = s.json()
    assert data["total_places"] == 0
    assert data["by_status"] == {}
    assert data["total_cost_cents"] == 0


# ---------------- Run lifecycle ----------------


@pytest.mark.anyio
async def test_run_start_fails_without_pipeline(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={"name": "NoPipe", "slug": "no-pipe", "queries": ["q"]},
    )
    cid = r.json()["id"]
    s = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert s.status_code == 400
    assert "Pipeline" in s.json()["detail"]


@pytest.mark.anyio
async def test_run_start_fails_without_queries(client):
    # Create a pipeline first
    p = await client.post(
        "/api/v1/engagement/pipelines",
        headers=HEADERS,
        json={"name": "X", "slug": "x", "channels": ["email"]},
    )
    pid = p.json()["id"]

    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "NoQ",
            "slug": "no-q",
            "queries": [],
            "target_engagement_pipeline_id": pid,
        },
    )
    cid = r.json()["id"]

    s = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert s.status_code == 400
    assert "Suchkonfiguration" in s.json()["detail"]


@pytest.mark.anyio
async def test_run_start_success_and_duplicate_protection(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "RunTest",
            "slug": "run-test",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]

    first = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert first.status_code == 201
    assert first.json()["status"] == "queued"
    assert first.json()["current_stage"] == "places"

    dup = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert dup.status_code == 400
    assert "laeuft bereits" in dup.json()["detail"]


@pytest.mark.anyio
async def test_pause_and_resume_run(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "PauseRes",
            "slug": "pause-res",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]
    run = (
        await client.post(f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS)
    ).json()
    rid = run["id"]

    p = await client.post(f"/api/v1/leadgen/runs/{rid}/pause", headers=HEADERS)
    assert p.status_code == 200
    assert p.json()["status"] == "paused"

    res = await client.post(f"/api/v1/leadgen/runs/{rid}/resume", headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["status"] == "queued"

    # resume when already queued should error
    err = await client.post(f"/api/v1/leadgen/runs/{rid}/resume", headers=HEADERS)
    assert err.status_code == 400


# ---------------- Enrich-only run ----------------


@pytest.mark.anyio
async def test_enrich_run_starts_at_llm_stage(client):
    """POST /campaigns/{id}/runs/enrich queues a run directly at stage 'llm'."""
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "EnrichOnly",
            "slug": "enrich-only",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]

    s = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich",
        headers=HEADERS,
        json={"limit": 100, "sampling": "top_rated"},
    )
    assert s.status_code == 201, s.text
    data = s.json()
    assert data["current_stage"] == "llm"
    assert data["status"] == "queued"
    assert data["stage_state"]["enrich_only"] is True
    assert data["stage_state"]["max_override"] == 100
    assert data["stage_state"]["sampling"] == "top_rated"


@pytest.mark.anyio
async def test_enrich_run_default_sampling_is_top_rated(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "EnrichDef",
            "slug": "enrich-def",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]
    s = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich",
        headers=HEADERS,
        json={"limit": 50},
    )
    assert s.status_code == 201
    assert s.json()["stage_state"]["sampling"] == "top_rated"


@pytest.mark.anyio
async def test_enrich_run_blocks_when_active_run_exists(client):
    """Cannot start an enrich run while another run is active."""
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "EnrichDup",
            "slug": "enrich-dup",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]

    first = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert first.status_code == 201

    enrich = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich",
        headers=HEADERS,
        json={"limit": 100},
    )
    assert enrich.status_code == 400
    assert "laeuft bereits" in enrich.json()["detail"]


@pytest.mark.anyio
async def test_enrich_run_validates_limit_and_sampling(client):
    r = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "EnrichVal",
            "slug": "enrich-val",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = r.json()["id"]

    bad_limit = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich",
        headers=HEADERS,
        json={"limit": 0, "sampling": "top_rated"},
    )
    assert bad_limit.status_code == 422

    bad_sampling = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs/enrich",
        headers=HEADERS,
        json={"limit": 10, "sampling": "magic"},
    )
    assert bad_sampling.status_code == 422


# ---------------- Worker with mocked places client ----------------


class _FakePlacesClient:
    """In-memory Places client for worker tests."""

    def __init__(self, pages_by_query: dict[str, list[list[dict]]]) -> None:
        self._pages = pages_by_query
        self.call_log: list[tuple[str, str | None]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None

    async def aclose(self):
        return None

    async def text_search(
        self,
        query: str,
        *,
        language_code: str = "de",
        region_code: str = "DE",
        page_token: str | None = None,
        page_size: int = 20,
    ):
        from app.leadgen.places_client import SearchPage, _parse_place

        self.call_log.append((query, page_token))
        pages = self._pages.get(query, [])
        idx = int(page_token) if page_token else 0
        if idx >= len(pages):
            return SearchPage(places=[], next_page_token=None)
        page_places = [_parse_place(p) for p in pages[idx]]
        next_token = str(idx + 1) if idx + 1 < len(pages) else None
        return SearchPage(places=page_places, next_page_token=next_token)


@pytest.mark.anyio
async def test_worker_processes_places_stage(client, db_session):
    """Run the worker against a mocked Places client and verify persistence."""
    from app.leadgen.worker import run_once

    # Create campaign + run
    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "WorkerTest",
            "slug": "worker-test",
            "queries": ["Elektriker Berlin", "Elektroinstallation Hamburg"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    run_resp = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    rid = run_resp.json()["id"]

    fake_pages = {
        "Elektriker Berlin": [
            [
                {"id": "p1", "displayName": {"text": "Elektro A"}},
                {"id": "p2", "displayName": {"text": "Elektro B"}},
            ],
            [
                {"id": "p3", "displayName": {"text": "Elektro C"}},
            ],
        ],
        "Elektroinstallation Hamburg": [
            [{"id": "p4", "displayName": {"text": "Hamburg Elektro"}}],
        ],
    }
    fake = _FakePlacesClient(fake_pages)

    result = await run_once(
        db_session,
        tenant_id="go4energy",
        run_id=rid,
        places_client_factory=lambda: fake,
        cost_cents_per_request=3,
    )
    assert result["status"] == "ok"
    assert result["success"] == 4
    # 3 API calls for query 1 (page0, page1, page2-empty-break? no, page2 has data),
    # plus 1 for query 2 = min 3 calls. With max_pages=3 default and our fake giving
    # 2 pages for q1 + stop, we expect 2+1 = 3 calls.
    assert len(fake.call_log) >= 3
    assert result["cost_cents"] >= 9

    # Verify places landed in DB
    places_resp = await client.get(
        f"/api/v1/leadgen/campaigns/{cid}/places", headers=HEADERS
    )
    data = places_resp.json()
    assert data["total"] == 4
    names = {p["name"] for p in data["items"]}
    assert names == {"Elektro A", "Elektro B", "Elektro C", "Hamburg Elektro"}


@pytest.mark.anyio
async def test_worker_deduplicates_across_queries(client, db_session):
    """Same google_place_id returned by two queries must be inserted once."""
    from app.leadgen.worker import run_once

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "Dedup",
            "slug": "dedup",
            "queries": ["q1", "q2"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    rid = (
        await client.post(f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS)
    ).json()["id"]

    fake_pages = {
        "q1": [[{"id": "X", "displayName": {"text": "Shared"}}]],
        "q2": [[{"id": "X", "displayName": {"text": "Shared"}}]],
    }
    fake = _FakePlacesClient(fake_pages)

    result = await run_once(
        db_session,
        tenant_id="go4energy",
        run_id=rid,
        places_client_factory=lambda: fake,
        cost_cents_per_request=3,
    )
    assert result["status"] == "ok"
    assert result["success"] == 1  # only one distinct place
    assert result["processed"] == 2  # but two results processed (one dup)


# ---------------- Place reject ----------------


@pytest.mark.anyio
async def test_reject_place(client, db_session):
    from app.leadgen.worker import run_once

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "RejTest",
            "slug": "rej-test",
            "queries": ["q"],
            "create_new_pipeline": True,
        },
    )
    cid = c.json()["id"]
    rid = (
        await client.post(f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS)
    ).json()["id"]

    fake = _FakePlacesClient({"q": [[{"id": "p1", "displayName": {"text": "X"}}]]})
    await run_once(
        db_session,
        tenant_id="go4energy",
        run_id=rid,
        places_client_factory=lambda: fake,
    )

    places = (
        await client.get(f"/api/v1/leadgen/campaigns/{cid}/places", headers=HEADERS)
    ).json()
    pid = places["items"][0]["id"]

    r = await client.post(
        f"/api/v1/leadgen/places/{pid}/reject",
        headers=HEADERS,
        json={"reason": "Kein PV-Bezug"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"
    assert r.json()["rejected_reason"] == "Kein PV-Bezug"


# ---------------- Places Client: geo helpers + nearby search ----------------


def test_rectangle_helper_builds_expected_payload():
    from app.leadgen.places_client import rectangle

    r = rectangle(south=47.2, west=5.8, north=55.1, east=15.1)
    assert r == {
        "rectangle": {
            "low": {"latitude": 47.2, "longitude": 5.8},
            "high": {"latitude": 55.1, "longitude": 15.1},
        }
    }


def test_circle_helper_caps_radius_at_50000m():
    from app.leadgen.places_client import circle

    within = circle(lat=52.5, lng=13.4, radius_m=30000)
    assert within["circle"]["radius"] == 30000

    capped = circle(lat=52.5, lng=13.4, radius_m=80000)
    assert capped["circle"]["radius"] == 50000.0


@pytest.mark.anyio
async def test_text_search_passes_location_restriction_in_body():
    """Text search must forward locationRestriction into the request body."""
    import httpx

    from app.leadgen.places_client import GooglePlacesClient, rectangle

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"places": [], "nextPageToken": None})

    transport = httpx.MockTransport(handler)
    async with GooglePlacesClient(api_key="k", qps=100, transport=transport) as c:
        await c.text_search(
            "Elektriker",
            location_restriction=rectangle(south=47, west=5, north=55, east=15),
        )

    assert "places:searchText" in captured["url"]
    assert "locationRestriction" in captured["body"]
    assert '"rectangle"' in captured["body"]


@pytest.mark.anyio
async def test_nearby_search_builds_correct_request():
    """Nearby Search posts to searchNearby with circle + includedTypes."""
    import httpx

    from app.leadgen.places_client import GooglePlacesClient

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "places": [
                    {
                        "id": "p1",
                        "displayName": {"text": "Test Elektro"},
                        "types": ["electrician"],
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with GooglePlacesClient(api_key="k", qps=100, transport=transport) as c:
        page = await c.nearby_search(
            center_lat=52.52,
            center_lng=13.40,
            radius_m=20000,
            included_types=["electrician"],
        )

    assert "places:searchNearby" in captured["url"]
    assert '"includedTypes"' in captured["body"]
    assert '"electrician"' in captured["body"]
    assert '"circle"' in captured["body"]
    assert len(page.places) == 1
    assert page.places[0].google_place_id == "p1"


@pytest.mark.anyio
async def test_nearby_search_requires_type_filter():
    """nearby_search must reject calls without included_types."""
    from app.leadgen.places_client import GooglePlacesClient, PlacesApiError

    async with GooglePlacesClient(api_key="k") as c:
        with pytest.raises(PlacesApiError, match="included_types"):
            await c.nearby_search(
                center_lat=52.52, center_lng=13.40, radius_m=10000
            )


# ---------------- Geo tiling ----------------


def test_geotile_subdivide_produces_4_equal_quadrants():
    from app.leadgen.geo_tiling import GeoTile

    t = GeoTile(south=0, west=0, north=10, east=10)
    subs = t.subdivide()
    assert len(subs) == 4
    # Bounding boxes must cover the parent exactly at the seams (lat 5, lng 5).
    # Corners of the 4 quadrants.
    lats = {(s.south, s.north) for s in subs}
    lngs = {(s.west, s.east) for s in subs}
    assert lats == {(0, 5), (5, 10)}
    assert lngs == {(0, 5), (5, 10)}
    # Total area is within 1% of parent (Mercator distortion at non-equator).
    total_area = sum(s.area_km2 for s in subs)
    assert abs(total_area - t.area_km2) / t.area_km2 < 0.01


def test_geotile_rejects_invalid_bounds():
    from app.leadgen.geo_tiling import GeoTile

    with pytest.raises(ValueError):
        GeoTile(south=10, west=0, north=5, east=10)
    with pytest.raises(ValueError):
        GeoTile(south=0, west=10, north=10, east=5)


def test_geotile_rectangle_payload_shape():
    from app.leadgen.geo_tiling import GeoTile

    t = GeoTile(south=47.2, west=5.8, north=55.1, east=15.1)
    payload = t.to_rectangle_payload()
    assert payload["rectangle"]["low"] == {"latitude": 47.2, "longitude": 5.8}
    assert payload["rectangle"]["high"] == {"latitude": 55.1, "longitude": 15.1}


def test_inscribed_circle_respects_50km_cap():
    from app.leadgen.geo_tiling import GERMANY_BOUNDS

    lat, lng, radius_m = GERMANY_BOUNDS.inscribed_circle()
    assert radius_m == 50000.0
    assert 47.2 < lat < 55.1
    assert 5.8 < lng < 15.1


def test_build_initial_tiles_germany():
    from app.leadgen.geo_tiling import GERMANY_BOUNDS, build_initial_tiles

    tiles = build_initial_tiles(scope="germany")
    assert tiles == [GERMANY_BOUNDS]


def test_build_initial_tiles_bundesland():
    from app.leadgen.geo_tiling import BUNDESLAND_BOUNDS, build_initial_tiles

    tiles = build_initial_tiles(scope="bundesland", bundesland="bayern")
    assert tiles == [BUNDESLAND_BOUNDS["bayern"]]


def test_build_initial_tiles_bundesland_invalid():
    from app.leadgen.geo_tiling import build_initial_tiles

    with pytest.raises(ValueError):
        build_initial_tiles(scope="bundesland", bundesland="atlantis")


def test_build_initial_tiles_circle_around_braunschweig():
    from app.leadgen.geo_tiling import build_initial_tiles

    tiles = build_initial_tiles(
        scope="circle", center_lat=52.266, center_lng=10.525, radius_km=30
    )
    assert len(tiles) == 1
    t = tiles[0]
    assert t.contains(52.266, 10.525)
    assert abs(t.height_km - 60) < 0.1


def test_should_subdivide_saturated_tile():
    from app.leadgen.geo_tiling import (
        GeoTile,
        TileProcessingResult,
        should_subdivide,
    )

    big = GeoTile(south=52, west=13, north=53, east=14)  # ~70 x 110 km
    result = TileProcessingResult(tile=big, result_count=60, saturated=True)
    assert should_subdivide(result, min_tile_km=10, saturation_threshold=60)


def test_should_not_subdivide_below_min_tile_km():
    from app.leadgen.geo_tiling import (
        GeoTile,
        TileProcessingResult,
        should_subdivide,
    )

    tiny = GeoTile(south=52.00, west=13.00, north=52.05, east=13.05)  # ~5 x 3 km
    result = TileProcessingResult(tile=tiny, result_count=60, saturated=True)
    assert not should_subdivide(result, min_tile_km=10, saturation_threshold=60)


def test_should_not_subdivide_unsaturated_tile():
    from app.leadgen.geo_tiling import (
        GeoTile,
        TileProcessingResult,
        should_subdivide,
    )

    big = GeoTile(south=52, west=13, north=53, east=14)
    result = TileProcessingResult(tile=big, result_count=23, saturated=False)
    assert not should_subdivide(result, min_tile_km=10, saturation_threshold=60)


# ---------------- Source config parsing ----------------


def test_parse_google_places_source_config_defaults():
    from app.leadgen.source_config import parse_source_config

    cfg = parse_source_config("google_places", {})
    assert cfg.search_modes.nearby is True
    assert cfg.search_modes.text is True
    assert cfg.geographic.mode == "germany"
    assert cfg.min_tile_km == 10.0
    assert cfg.max_api_calls == 2000


def test_parse_google_places_source_config_full():
    from app.leadgen.source_config import parse_source_config

    cfg = parse_source_config(
        "google_places",
        {
            "search_modes": {"nearby": True, "text": False},
            "nearby_types": ["electrician", "plumber"],
            "text_synonyms": ["Elektroinstallation"],
            "geographic": {
                "mode": "circle",
                "center_lat": 52.266,
                "center_lng": 10.525,
                "radius_km": 30,
            },
            "min_tile_km": 5,
            "max_api_calls": 500,
        },
    )
    assert cfg.search_modes.nearby is True
    assert cfg.search_modes.text is False
    assert cfg.nearby_types == ["electrician", "plumber"]
    assert cfg.geographic.mode == "circle"
    assert cfg.geographic.radius_km == 30
    assert cfg.min_tile_km == 5
    assert cfg.max_api_calls == 500


def test_parse_bundesland_normalises_key():
    from app.leadgen.source_config import parse_source_config

    cfg = parse_source_config(
        "google_places",
        {"geographic": {"mode": "bundesland", "bundesland": "Baden-Württemberg"}},
    )
    # Note: ue/ö expansion is out of scope; we only lower+underscore.
    assert cfg.geographic.bundesland == "baden_württemberg"


def test_parse_source_config_rejects_unknown_source():
    from app.leadgen.source_config import parse_source_config

    with pytest.raises(ValueError, match="unknown source"):
        parse_source_config("odoo", {})


def test_max_api_calls_out_of_range_rejected():
    from pydantic import ValidationError

    from app.leadgen.source_config import parse_source_config

    with pytest.raises(ValidationError):
        parse_source_config("google_places", {"max_api_calls": 0})
    with pytest.raises(ValidationError):
        parse_source_config("google_places", {"max_api_calls": 1_000_000})


# ---------------- Worker: hybrid tile mode ----------------


class _FakeHybridClient:
    """Places client for the tile-based hybrid path.

    Returns configurable results for nearby_search and text_search calls.
    """

    def __init__(
        self,
        *,
        nearby_places: list[dict] | None = None,
        text_places: list[dict] | None = None,
    ) -> None:
        self._nearby = nearby_places or []
        self._text = text_places or []
        self.nearby_calls: list[dict] = []
        self.text_calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None

    async def aclose(self):
        return None

    async def nearby_search(
        self,
        *,
        center_lat,
        center_lng,
        radius_m,
        included_types=None,
        included_primary_types=None,
        excluded_types=None,
        language_code="de",
        region_code="DE",
        max_result_count=20,
    ):
        from app.leadgen.places_client import SearchPage, _parse_place

        self.nearby_calls.append(
            {
                "center": (center_lat, center_lng),
                "radius_m": radius_m,
                "types": included_types,
            }
        )
        return SearchPage(
            places=[_parse_place(p) for p in self._nearby],
            next_page_token=None,
        )

    async def text_search(
        self,
        query,
        *,
        language_code="de",
        region_code="DE",
        page_token=None,
        page_size=20,
        location_restriction=None,
        location_bias=None,
    ):
        from app.leadgen.places_client import SearchPage, _parse_place

        self.text_calls.append(
            {
                "query": query,
                "location_restriction": location_restriction,
            }
        )
        return SearchPage(
            places=[_parse_place(p) for p in self._text],
            next_page_token=None,
        )


@pytest.mark.anyio
async def test_worker_hybrid_crawls_tile_with_nearby_and_text(client, db_session):
    """Hybrid config triggers tile crawl with both nearby and text searches."""
    from app.leadgen.worker import run_once

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "Hybrid",
            "slug": "hybrid-test",
            "queries": [],
            "create_new_pipeline": True,
            "source": "google_places",
            "source_config": {
                "search_modes": {"nearby": True, "text": True},
                "nearby_types": ["electrician"],
                "text_synonyms": ["Elektroinstallation"],
                "geographic": {
                    "mode": "circle",
                    "center_lat": 52.266,
                    "center_lng": 10.525,
                    "radius_km": 15,
                },
                "min_tile_km": 10,
                "max_api_calls": 50,
            },
        },
    )
    assert c.status_code == 201
    cid = c.json()["id"]
    rid = (
        await client.post(f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS)
    ).json()["id"]

    fake = _FakeHybridClient(
        nearby_places=[
            {
                "id": "nearby1",
                "displayName": {"text": "Elektro Nord"},
                "types": ["electrician"],
            }
        ],
        text_places=[
            {
                "id": "text1",
                "displayName": {"text": "Elektroinstallation Sued"},
                "types": ["electrician"],
            }
        ],
    )
    await run_once(
        db_session,
        tenant_id="go4energy",
        run_id=rid,
        places_client_factory=lambda: fake,
    )

    # Both endpoints were hit
    assert len(fake.nearby_calls) >= 1
    assert fake.nearby_calls[0]["types"] == ["electrician"]
    assert len(fake.text_calls) >= 1
    assert fake.text_calls[0]["query"] == "Elektroinstallation"
    assert fake.text_calls[0]["location_restriction"] is not None
    assert "rectangle" in fake.text_calls[0]["location_restriction"]

    # Both places are persisted
    places = (
        await client.get(
            f"/api/v1/leadgen/campaigns/{cid}/places", headers=HEADERS
        )
    ).json()
    names = {p["name"] for p in places["items"]}
    assert "Elektro Nord" in names
    assert "Elektroinstallation Sued" in names


@pytest.mark.anyio
async def test_worker_hybrid_respects_max_api_calls_hardcap(client, db_session):
    """Run must stop when max_api_calls budget is exhausted."""
    from app.leadgen.worker import run_once

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "BudgetCap",
            "slug": "budget-cap",
            "queries": [],
            "create_new_pipeline": True,
            "source": "google_places",
            "source_config": {
                "search_modes": {"nearby": True, "text": False},
                "nearby_types": ["electrician"],
                "text_synonyms": [],
                "geographic": {"mode": "germany"},
                "min_tile_km": 1,
                "max_api_calls": 1,
            },
        },
    )
    cid = c.json()["id"]
    rid = (
        await client.post(f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS)
    ).json()["id"]

    # Return saturated results so the tile wants to subdivide.
    saturated = [
        {"id": f"p{i}", "displayName": {"text": f"Firma {i}"}} for i in range(20)
    ]
    fake = _FakeHybridClient(nearby_places=saturated)
    await run_once(
        db_session,
        tenant_id="go4energy",
        run_id=rid,
        places_client_factory=lambda: fake,
    )

    # Budget was 1 call. The worker must have stopped after exactly 1 call.
    assert len(fake.nearby_calls) == 1


@pytest.mark.anyio
async def test_intake_endpoint_returns_parsed_suggestion(client, monkeypatch):
    """Intake endpoint calls Claude Haiku and returns a validated suggestion."""
    from app.leadgen import intake as intake_module

    fake_response = """```json
{
  "nearby_types": ["electrician"],
  "text_synonyms": ["Elektroinstallation", "Elektrotechnik", "Elektromeister"],
  "geographic": {"mode": "germany"},
  "min_tile_km": 10,
  "max_api_calls": 1500,
  "estimated_calls_low": 800,
  "estimated_calls_high": 1500,
  "estimated_cost_usd_low": 25.6,
  "estimated_cost_usd_high": 48.0,
  "estimated_results_low": 15000,
  "estimated_results_high": 40000,
  "reasoning": "Elektriker bundesweit mit 3 Synonymen und Google-Type."
}
```"""

    async def fake_generate(self, *, provider, model, system_prompt, user_prompt,
                            temperature=0.7, max_tokens=2048):
        return fake_response

    monkeypatch.setattr(
        intake_module.LLMService, "generate_with_config", fake_generate
    )

    r = await client.post(
        "/api/v1/leadgen/intake",
        headers=HEADERS,
        json={"text": "Alle Elektrobetriebe in Deutschland"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["nearby_types"] == ["electrician"]
    assert "Elektroinstallation" in data["text_synonyms"]
    assert data["geographic"]["mode"] == "germany"
    assert data["estimated_calls_high"] == 1500
    assert "Elektriker" in data["reasoning"]


@pytest.mark.anyio
async def test_intake_filters_invented_place_types(client, monkeypatch):
    """LLM-returned place types not in the whitelist must be stripped."""
    from app.leadgen import intake as intake_module

    fake_response = """{
  "nearby_types": ["electrician", "made_up_type", "plumber"],
  "text_synonyms": ["Test"],
  "geographic": {"mode": "germany"},
  "min_tile_km": 10,
  "max_api_calls": 500,
  "estimated_calls_low": 100,
  "estimated_calls_high": 300,
  "estimated_cost_usd_low": 3.2,
  "estimated_cost_usd_high": 9.6,
  "estimated_results_low": 500,
  "estimated_results_high": 2000,
  "reasoning": "Test."
}"""

    async def fake_generate(self, *, provider, model, system_prompt, user_prompt,
                            temperature=0.7, max_tokens=2048):
        return fake_response

    monkeypatch.setattr(
        intake_module.LLMService, "generate_with_config", fake_generate
    )

    r = await client.post(
        "/api/v1/leadgen/intake",
        headers=HEADERS,
        json={"text": "Test fuer Whitelist-Filter"},
    )
    assert r.status_code == 200
    assert r.json()["nearby_types"] == ["electrician", "plumber"]


@pytest.mark.anyio
async def test_intake_rejects_empty_text(client):
    r = await client.post(
        "/api/v1/leadgen/intake",
        headers=HEADERS,
        json={"text": ""},
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_intake_returns_full_wizard_suggestion(client, monkeypatch):
    """Intake must surface name, slug, search_modes and pipeline_mode for the wizard."""
    from app.leadgen import intake as intake_module

    fake_response = """{
  "name_suggestion": "Lastmanagement-Partner MFH Deutschland",
  "slug_suggestion": "lastmanagement-partner-mfh",
  "search_modes": {"nearby": true, "text": true},
  "nearby_types": ["electrician"],
  "text_synonyms": ["Elektroinstallation", "Photovoltaik"],
  "geographic": {"mode": "germany"},
  "min_tile_km": 10,
  "max_api_calls": 1500,
  "pipeline_mode": "smart",
  "estimated_calls_low": 800,
  "estimated_calls_high": 1500,
  "estimated_cost_usd_low": 25.6,
  "estimated_cost_usd_high": 48.0,
  "estimated_results_low": 5000,
  "estimated_results_high": 12000,
  "reasoning": "Elektrofachbetriebe und PV-Anbieter bundesweit.",
  "target_profile": "ZIELGRUPPE: ...",
  "output_description": "Wallbox-Erfahrung, MFH-Projekte, Mitarbeiterzahl."
}"""

    async def fake_generate(self, *, provider, model, system_prompt, user_prompt,
                            temperature=0.7, max_tokens=2048):
        return fake_response

    monkeypatch.setattr(
        intake_module.LLMService, "generate_with_config", fake_generate
    )

    r = await client.post(
        "/api/v1/leadgen/intake",
        headers=HEADERS,
        json={"text": "Wir suchen Elektrofachbetriebe und PV-Anbieter fuer MFH-Lastmanagement"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name_suggestion"] == "Lastmanagement-Partner MFH Deutschland"
    assert data["slug_suggestion"] == "lastmanagement-partner-mfh"
    assert data["search_modes"] == {"nearby": True, "text": True}
    assert data["pipeline_mode"] == "smart"
    assert data["target_profile"].startswith("ZIELGRUPPE")


@pytest.mark.anyio
async def test_intake_clamps_invalid_pipeline_mode(client, monkeypatch):
    """LLM-returned pipeline_mode outside the whitelist falls back to 'smart'."""
    from app.leadgen import intake as intake_module

    fake_response = """{
  "name_suggestion": "X",
  "slug_suggestion": "x",
  "search_modes": {"nearby": false, "text": true},
  "nearby_types": [],
  "text_synonyms": ["Test"],
  "geographic": {"mode": "germany"},
  "min_tile_km": 10,
  "max_api_calls": 100,
  "pipeline_mode": "magic",
  "estimated_calls_low": 10,
  "estimated_calls_high": 50,
  "estimated_cost_usd_low": 0.32,
  "estimated_cost_usd_high": 1.6,
  "estimated_results_low": 50,
  "estimated_results_high": 200,
  "reasoning": "Test."
}"""

    async def fake_generate(self, *, provider, model, system_prompt, user_prompt,
                            temperature=0.7, max_tokens=2048):
        return fake_response

    monkeypatch.setattr(
        intake_module.LLMService, "generate_with_config", fake_generate
    )

    r = await client.post(
        "/api/v1/leadgen/intake",
        headers=HEADERS,
        json={"text": "Test fallback"},
    )
    assert r.status_code == 200
    assert r.json()["pipeline_mode"] == "smart"


@pytest.mark.anyio
async def test_run_start_accepts_hybrid_config_without_queries(client):
    """A campaign with only source_config.nearby_types should start cleanly."""
    p = await client.post(
        "/api/v1/engagement/pipelines",
        headers=HEADERS,
        json={"name": "HybNoQ", "slug": "hyb-no-q", "channels": ["email"]},
    )
    pid = p.json()["id"]

    c = await client.post(
        "/api/v1/leadgen/campaigns",
        headers=HEADERS,
        json={
            "name": "HybNoQ",
            "slug": "hyb-no-q",
            "queries": [],
            "target_engagement_pipeline_id": pid,
            "source": "google_places",
            "source_config": {
                "nearby_types": ["electrician"],
                "geographic": {"mode": "germany"},
            },
        },
    )
    assert c.status_code == 201
    cid = c.json()["id"]

    r = await client.post(
        f"/api/v1/leadgen/campaigns/{cid}/runs", headers=HEADERS
    )
    assert r.status_code == 201


# ---------------- LLM stage: no-website branch (homepage-sales leads) ----------------


@pytest.mark.anyio
async def test_llm_stage_no_website_places_get_synthetic_top_score(db_session):
    """Places without a website must skip the LLM and become top-score leads.

    For homepage-sales campaigns the most valuable prospects are the ones with
    no website at all. The LLM stage should pick them up despite the missing
    URL, write a synthetic LLMInsights row with target_match_score=10, and not
    spend any money.
    """
    import httpx

    from app.leadgen.models import (
        LeadgenCampaign,
        LeadgenLLMInsights,
        LeadgenPlace,
        LeadgenRun,
    )
    from app.leadgen.source_config import LLMStageConfig
    from app.leadgen.worker import _process_llm_stage

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="HomepageSales",
        slug="homepage-sales-llm",
        queries=["Arztpraxis Berlin"],
        source="google_places",
        source_config={},
    )
    db_session.add(campaign)
    await db_session.flush()

    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="llm",
        status="running",
    )
    db_session.add(run)
    await db_session.flush()

    no_site = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        run_id=run.id,
        google_place_id="ChIJ_no_site",
        name="Praxis Ohne Homepage",
        website=None,
        status="discovered",
    )
    blank_site = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        run_id=run.id,
        google_place_id="ChIJ_blank_site",
        name="Praxis Mit Leerstring",
        website="   ",
        status="discovered",
    )
    db_session.add_all([no_site, blank_site])
    await db_session.flush()

    # If the LLM service or HTTP client gets called, the test fails — neither
    # should happen for no-website places.
    class _ExplodingLLM:
        async def generate_with_usage(self, *args, **kwargs):
            raise AssertionError("LLM must not be called for no-website places")

    async with httpx.AsyncClient() as http_client:
        done = await _process_llm_stage(
            db_session,
            run=run,
            campaign=campaign,
            cfg=LLMStageConfig(target_profile="Arztpraxen ohne Homepage"),
            http_client=http_client,
            llm=_ExplodingLLM(),
        )

    # Stage returns False (more work could come) but with no site_places left
    # we expect both no-website places to be processed in this single call.
    assert done is False

    await db_session.refresh(no_site)
    await db_session.refresh(blank_site)
    await db_session.refresh(run)

    assert no_site.status == "llm_done"
    assert blank_site.status == "llm_done"

    rows = (
        await db_session.execute(
            select(LeadgenLLMInsights).where(
                LeadgenLLMInsights.place_id.in_([no_site.id, blank_site.id])
            )
        )
    ).scalars().all()
    assert len(rows) == 2
    for r in rows:
        assert r.target_match_score == 10
        assert r.cost_cents == 0
        assert r.model_used == "skip:no_website"
        assert "keine Homepage" in (r.red_flags or [])

    assert run.cost_cents == 0
    assert run.success_count == 2
    assert run.error_count == 0
    state = run.stage_state or {}
    assert state.get("places_processed") == 2
    assert state.get("places_succeeded") == 2
    assert state.get("llm_cost_cents", 0) == 0


# ---------------- website_verify helper unit tests ----------------


def test_pick_homepage_filters_known_portals():
    """Portal hits (jameda, doctolib, business directories) must be skipped."""
    from app.leadgen.website_verify import pick_homepage_from_results

    results = [
        {"url": "https://www.jameda.de/berlin/aerzte/praxis-mueller/uebersicht/12345"},
        {"url": "https://www.doctolib.de/hausarzt/berlin/dr-mueller"},
        {"url": "https://www.gelbeseiten.de/eintrag/praxis-mueller-berlin"},
        {"url": "https://praxis-mueller-berlin.de/"},
    ]
    result = pick_homepage_from_results(results, name="Praxis Müller")
    assert result == "https://praxis-mueller-berlin.de/"


def test_pick_homepage_requires_name_match():
    """Non-portal hits that don't match the business name are rejected."""
    from app.leadgen.website_verify import pick_homepage_from_results

    results = [
        {"url": "https://random-news-site.de/article/123"},
        {"url": "https://other-business.de/"},
    ]
    assert pick_homepage_from_results(results, name="Praxis Müller") is None


def test_pick_homepage_handles_umlaut_variants():
    """ä→ae transliteration is honoured when matching name to domain."""
    from app.leadgen.website_verify import pick_homepage_from_results

    results = [{"url": "https://praxis-muehlhausen.de/"}]
    assert (
        pick_homepage_from_results(results, name="Praxis Mühlhausen")
        == "https://praxis-muehlhausen.de/"
    )


def test_pick_homepage_extra_blacklist_applied():
    """Campaign-level extra blacklist hosts are rejected even on name match."""
    from app.leadgen.website_verify import pick_homepage_from_results

    results = [
        {"url": "https://praxis-mueller.local-portal.de/profil/123"},
        {"url": "https://praxis-mueller.de/"},
    ]
    assert (
        pick_homepage_from_results(
            results,
            name="Praxis Mueller",
            extra_blacklist=("local-portal.de",),
        )
        == "https://praxis-mueller.de/"
    )


def test_detect_booking_link_finds_doctolib_in_payload():
    """Booking platforms anywhere in the raw payload count as a calendar offer."""
    from app.leadgen.website_verify import detect_booking_link

    payload = {
        "websiteUri": "https://praxis.example.de",
        "googleMapsLinks": {
            "appointmentsLink": "https://www.doctolib.de/hausarzt/berlin/x"
        },
    }
    assert detect_booking_link(payload) is True


def test_detect_booking_link_returns_false_when_absent():
    """No booking indicator anywhere → False (drives the flag)."""
    from app.leadgen.website_verify import detect_booking_link

    payload = {
        "displayName": {"text": "Praxis Mueller"},
        "websiteUri": "https://praxis-mueller.de",
        "rating": 4.5,
    }
    assert detect_booking_link(payload) is False


# ---------------- LLM stage: Serper-verify integration ----------------


@pytest.mark.anyio
async def test_llm_stage_serper_promotes_place_with_hidden_homepage(
    db_session, monkeypatch
):
    """If Serper finds a real homepage for a no-website place, it must be
    promoted into the normal LLM path AND tagged homepage_not_in_google."""
    import httpx

    from app.config import settings as app_settings
    from app.leadgen import worker as worker_mod
    from app.leadgen.homepage_analyzer import LLMAnalysis
    from app.leadgen.models import (
        LeadgenCampaign,
        LeadgenLLMInsights,
        LeadgenPlace,
        LeadgenRun,
    )
    from app.leadgen.source_config import LLMStageConfig

    monkeypatch.setattr(app_settings, "serper_api_key", "test-key", raising=False)

    async def fake_verify(*, name, city, serper_api_key, extra_blacklist):
        if "Mueller" in name:
            return "https://praxis-mueller-berlin.de/"
        return None

    async def fake_analyze(place, *, cfg, http_client, llm, semaphore, prompt_template):
        return place.id, LLMAnalysis(
            target_match_score=7,
            personalization_hook="real LLM result",
            services=["Allgemeinmedizin"],
            model_used="claude-haiku-4-5",
            cost_cents=1,
        )

    monkeypatch.setattr(worker_mod, "verify_no_website", fake_verify)
    monkeypatch.setattr(worker_mod, "_analyze_one_place", fake_analyze)

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="Verify",
        slug="verify-camp",
        queries=["Arztpraxis"],
        source="google_places",
        source_config={},
    )
    db_session.add(campaign)
    await db_session.flush()
    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="llm",
        status="running",
    )
    db_session.add(run)
    await db_session.flush()

    found = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        run_id=run.id,
        google_place_id="P_FOUND",
        name="Praxis Mueller",
        address_city="Berlin",
        website=None,
        status="discovered",
        enrichment_flags={},
    )
    not_found = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        run_id=run.id,
        google_place_id="P_NOT_FOUND",
        name="Praxis Schmidt",
        address_city="Berlin",
        website=None,
        status="discovered",
        enrichment_flags={},
    )
    db_session.add_all([found, not_found])
    await db_session.flush()

    async with httpx.AsyncClient() as http_client:
        await worker_mod._process_llm_stage(
            db_session,
            run=run,
            campaign=campaign,
            cfg=LLMStageConfig(),
            http_client=http_client,
            llm=object(),
        )

    await db_session.refresh(found)
    await db_session.refresh(not_found)

    # Found: website set, flag set, normal LLM path
    assert found.website == "https://praxis-mueller-berlin.de/"
    assert found.enrichment_flags.get("homepage_not_in_google") is True
    assert found.enrichment_flags.get("serper_checked_at")
    found_insights = (
        await db_session.execute(
            select(LeadgenLLMInsights).where(LeadgenLLMInsights.place_id == found.id)
        )
    ).scalar_one()
    assert found_insights.target_match_score == 7
    assert found_insights.model_used == "claude-haiku-4-5"

    # Not found: still no website, synthetic top-score, but serper_checked_at set
    assert not_found.website is None
    assert not_found.enrichment_flags.get("homepage_not_in_google") is None
    assert not_found.enrichment_flags.get("serper_checked_at")
    nf_insights = (
        await db_session.execute(
            select(LeadgenLLMInsights).where(LeadgenLLMInsights.place_id == not_found.id)
        )
    ).scalar_one()
    assert nf_insights.target_match_score == 10
    assert nf_insights.model_used == "skip:no_website"


@pytest.mark.anyio
async def test_llm_stage_skips_serper_when_disabled(db_session, monkeypatch):
    """If verify_no_website_via_serper=False, no Serper call regardless of key."""
    import httpx

    from app.config import settings as app_settings
    from app.leadgen import worker as worker_mod
    from app.leadgen.models import (
        LeadgenCampaign,
        LeadgenLLMInsights,
        LeadgenPlace,
        LeadgenRun,
    )
    from app.leadgen.source_config import LLMStageConfig

    monkeypatch.setattr(app_settings, "serper_api_key", "test-key", raising=False)

    async def boom(**kwargs):
        raise AssertionError("Serper must not be called when toggle is off")

    monkeypatch.setattr(worker_mod, "verify_no_website", boom)

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="Off",
        slug="serper-off",
        queries=["x"],
        source="google_places",
        source_config={},
    )
    db_session.add(campaign)
    await db_session.flush()
    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="llm",
        status="running",
    )
    db_session.add(run)
    await db_session.flush()
    place = LeadgenPlace(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        run_id=run.id,
        google_place_id="P_NS_OFF",
        name="Praxis OffSwitch",
        website=None,
        status="discovered",
        enrichment_flags={},
    )
    db_session.add(place)
    await db_session.flush()

    async with httpx.AsyncClient() as http_client:
        await worker_mod._process_llm_stage(
            db_session,
            run=run,
            campaign=campaign,
            cfg=LLMStageConfig(verify_no_website_via_serper=False),
            http_client=http_client,
            llm=object(),
        )

    await db_session.refresh(place)
    assert place.website is None
    insights = (
        await db_session.execute(
            select(LeadgenLLMInsights).where(LeadgenLLMInsights.place_id == place.id)
        )
    ).scalar_one()
    assert insights.target_match_score == 10
    # Serper was never called → no idempotency marker should have been written
    assert "serper_checked_at" not in (place.enrichment_flags or {})


# ---------------- Calendar flag during places-parse ----------------


@pytest.mark.anyio
async def test_upsert_places_sets_no_calendar_flag(db_session):
    """When campaign has flag_no_calendar=True and payload has no booking
    indicator, the inserted place gets enrichment_flags.no_calendar_in_google."""
    from app.leadgen.models import LeadgenCampaign, LeadgenPlace, LeadgenRun
    from app.leadgen.places_client import _parse_place
    from app.leadgen.worker import _upsert_places

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="CalFlag",
        slug="cal-flag",
        queries=["x"],
        source="google_places",
        source_config={"flag_no_calendar": True},
    )
    db_session.add(campaign)
    await db_session.flush()
    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="places",
        status="running",
    )
    db_session.add(run)
    await db_session.flush()

    no_cal = _parse_place(
        {
            "id": "ChIJ_no_cal",
            "displayName": {"text": "Praxis Without Calendar"},
            "websiteUri": "https://praxis-static.de",
        }
    )
    has_cal = _parse_place(
        {
            "id": "ChIJ_has_cal",
            "displayName": {"text": "Praxis With Calendar"},
            "websiteUri": "https://praxis-modern.de",
            "googleMapsLinks": {"appointmentsLink": "https://www.doctolib.de/x"},
        }
    )
    new_count, _ = await _upsert_places(
        db_session,
        tenant_id="go4energy",
        campaign=campaign,
        run=run,
        query="q",
        parsed=[no_cal, has_cal],
    )
    await db_session.flush()
    assert new_count == 2

    rows = (
        await db_session.execute(
            select(LeadgenPlace).where(LeadgenPlace.campaign_id == campaign.id)
        )
    ).scalars().all()
    by_gid = {r.google_place_id: r for r in rows}
    assert by_gid["ChIJ_no_cal"].enrichment_flags.get("no_calendar_in_google") is True
    assert (
        "no_calendar_in_google" not in (by_gid["ChIJ_has_cal"].enrichment_flags or {})
    )


@pytest.mark.anyio
async def test_upsert_places_no_calendar_flag_off_by_default(db_session):
    """Without flag_no_calendar, the calendar heuristic is skipped entirely."""
    from app.leadgen.models import LeadgenCampaign, LeadgenPlace, LeadgenRun
    from app.leadgen.places_client import _parse_place
    from app.leadgen.worker import _upsert_places

    campaign = LeadgenCampaign(
        tenant_id="go4energy",
        name="NoCalFlag",
        slug="no-cal-flag",
        queries=["x"],
        source="google_places",
        source_config={},
    )
    db_session.add(campaign)
    await db_session.flush()
    run = LeadgenRun(
        tenant_id="go4energy",
        campaign_id=campaign.id,
        current_stage="places",
        status="running",
    )
    db_session.add(run)
    await db_session.flush()

    parsed = _parse_place(
        {"id": "ChIJ_off", "displayName": {"text": "Praxis Off"}}
    )
    await _upsert_places(
        db_session,
        tenant_id="go4energy",
        campaign=campaign,
        run=run,
        query="q",
        parsed=[parsed],
    )
    await db_session.flush()

    place = (
        await db_session.execute(
            select(LeadgenPlace).where(LeadgenPlace.google_place_id == "ChIJ_off")
        )
    ).scalar_one()
    assert place.enrichment_flags == {}


# ---------------- stage_state helper unit tests ----------------


def test_stage_state_mark_running_is_idempotent():
    """Calling mark_running multiple times must not overwrite started_at."""
    from app.leadgen.stage_state import mark_stage_running

    state: dict = {}
    mark_stage_running(state, "places")
    first_started = state["stages"]["places"]["started_at"]
    mark_stage_running(state, "places")
    assert state["stages"]["places"]["started_at"] == first_started
    assert state["stages"]["places"]["status"] == "running"


def test_stage_state_mark_completed_sets_completion_timestamp():
    from app.leadgen.stage_state import mark_stage_completed, mark_stage_running

    state: dict = {}
    mark_stage_running(state, "llm")
    mark_stage_completed(state, "llm")
    entry = state["stages"]["llm"]
    assert entry["status"] == "completed"
    assert "started_at" in entry
    assert "completed_at" in entry


def test_stage_state_mark_skipped_records_reason():
    from app.leadgen.stage_state import mark_stage_skipped

    state: dict = {}
    mark_stage_skipped(state, "impressum", reason="pipeline_mode=smart")
    entry = state["stages"]["impressum"]
    assert entry["status"] == "skipped"
    assert entry["reason"] == "pipeline_mode=smart"


def test_stage_state_counters_delta_and_set():
    """delta entries increment, set_values overwrite, extra dict-merges."""
    from app.leadgen.stage_state import update_stage_counters

    state: dict = {}
    update_stage_counters(
        state, "verify", delta={"checked": 5, "homepages_found": 2}
    )
    update_stage_counters(state, "verify", delta={"checked": 3})
    update_stage_counters(state, "verify", set_values={"total": 100})
    update_stage_counters(state, "verify", extra={"sample_url": "https://x.de"})

    entry = state["stages"]["verify"]
    assert entry["checked"] == 8
    assert entry["homepages_found"] == 2
    assert entry["total"] == 100
    assert entry["extra"]["sample_url"] == "https://x.de"


def test_transition_stage_preserves_timeline_history():
    """Auto-chain transition keeps the stages dict alive across stages."""
    from app.leadgen.models import LeadgenRun
    from app.leadgen.worker import _transition_stage

    run = LeadgenRun(tenant_id="t", campaign_id=1, current_stage="places", status="running")
    run.stage_state = {
        "stages": {
            "places": {
                "status": "running",
                "started_at": "2026-04-26T10:00:00",
                "processed": 50,
                "succeeded": 50,
            }
        },
        "current_query_index": 3,
    }
    _transition_stage(run, mode="smart")  # places -> llm in smart mode
    assert run.current_stage == "llm"
    assert run.status == "queued"
    # places history preserved with completion mark
    places_entry = run.stage_state["stages"]["places"]
    assert places_entry["status"] == "completed"
    assert places_entry["processed"] == 50
    # legacy per-stage workspace was dropped
    assert "current_query_index" not in run.stage_state


def test_transition_stage_marks_skipped_at_completion():
    """When run completes, stages that were never run get explicit skipped status."""
    from app.leadgen.models import LeadgenRun
    from app.leadgen.worker import _transition_stage

    run = LeadgenRun(tenant_id="t", campaign_id=1, current_stage="llm", status="running")
    run.stage_state = {
        "stages": {
            "places": {"status": "completed"},
            "llm": {"status": "running"},
        }
    }
    _transition_stage(run, mode="smart")  # llm -> completed
    stages = run.stage_state["stages"]
    assert run.current_stage == "completed"
    assert stages["llm"]["status"] == "completed"
    # Impressum never ran in smart-mode -> explicit skipped
    assert stages["impressum"]["status"] == "skipped"
    assert "smart" in stages["impressum"]["reason"]
    # Verify never ran (no no-site places this run) -> also skipped
    assert stages["verify"]["status"] == "skipped"
