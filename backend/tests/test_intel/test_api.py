"""HTTP-API tests for /api/v1/intel/* — runs against the FastAPI ASGI
test client with Auth bypass + tenant header.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.conftest import TEST_AUTH_HEADERS

TENANT_HEADERS = {**TEST_AUTH_HEADERS, "X-Tenant-ID": "go4energy"}


@pytest_asyncio.fixture
async def tenant(client):
    """Ensure the go4energy tenant exists."""
    r = await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "go4energy", "tenant_name": "go4energy"},
    )
    assert r.status_code in (201, 409)
    return "go4energy"


# ─── Watch-Targets ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_and_list_target(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "Konkurrent A", "kind": "competitor"},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 201, r.text
    target = r.json()
    assert target["name"] == "Konkurrent A"
    assert target["kind"] == "competitor"
    assert target["is_active"] is True
    assert target["tenant_id"] == "go4energy"

    r = await client.get("/api/v1/intel/targets", headers=TENANT_HEADERS)
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "Konkurrent A" in names


@pytest.mark.anyio
async def test_create_rejects_invalid_kind(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "X", "kind": "spam"},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_update_target(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "ToUpdate", "kind": "competitor"},
        headers=TENANT_HEADERS,
    )
    tid = r.json()["id"]
    r = await client.put(
        f"/api/v1/intel/targets/{tid}",
        json={"name": "Updated", "is_active": False},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Updated"
    assert body["is_active"] is False


@pytest.mark.anyio
async def test_delete_target_is_soft(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "ToDelete", "kind": "regulator"},
        headers=TENANT_HEADERS,
    )
    tid = r.json()["id"]
    r = await client.delete(
        f"/api/v1/intel/targets/{tid}", headers=TENANT_HEADERS
    )
    assert r.status_code == 204
    # Still readable, but inactive
    r = await client.get(
        f"/api/v1/intel/targets/{tid}", headers=TENANT_HEADERS
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.anyio
async def test_get_unknown_target_404(client, tenant):
    r = await client.get("/api/v1/intel/targets/9999999", headers=TENANT_HEADERS)
    assert r.status_code == 404


# ─── Sources ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_and_list_source(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "ForSources", "kind": "competitor"},
        headers=TENANT_HEADERS,
    )
    tid = r.json()["id"]

    r = await client.post(
        f"/api/v1/intel/targets/{tid}/sources",
        json={
            "adapter": "web",
            "config": {"url": "https://example.com/"},
            "fetch_interval_sec": 3600,
        },
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 201, r.text
    src = r.json()
    assert src["adapter"] == "web"
    assert src["last_status"] == "pending"
    assert src["consecutive_failures"] == 0

    r = await client.get(
        f"/api/v1/intel/targets/{tid}/sources", headers=TENANT_HEADERS
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.anyio
async def test_source_interval_validation(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "IntervalCheck", "kind": "competitor"},
        headers=TENANT_HEADERS,
    )
    tid = r.json()["id"]
    # Below min (300s)
    r = await client.post(
        f"/api/v1/intel/targets/{tid}/sources",
        json={"adapter": "web", "config": {"url": "https://x"}, "fetch_interval_sec": 30},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 422


@pytest.mark.anyio
async def test_source_unknown_target_404(client, tenant):
    r = await client.post(
        "/api/v1/intel/targets/9999999/sources",
        json={"adapter": "web", "config": {"url": "https://x"}},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 404


# ─── Briefings ───────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_briefings_empty(client, tenant):
    r = await client.get("/api/v1/intel/briefings", headers=TENANT_HEADERS)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_get_unknown_briefing_404(client, tenant):
    r = await client.get(
        "/api/v1/intel/briefings/9999999", headers=TENANT_HEADERS
    )
    assert r.status_code == 404


# ─── Events ──────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_list_events_with_filters(client, tenant):
    r = await client.get(
        "/api/v1/intel/events",
        params={"min_significance": 0.5, "limit": 10},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_events_significance_bounds(client, tenant):
    r = await client.get(
        "/api/v1/intel/events",
        params={"min_significance": 1.5},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 422


# ─── Admin ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_embed_health_endpoint(client, tenant):
    """Probe the embedding backend (Ollama).

    Ollama runs on the dev host but is unreachable from the sandboxed
    test client; we therefore only assert the shape, not the value.
    """
    r = await client.get(
        "/api/v1/intel/admin/embed-health", headers=TENANT_HEADERS
    )
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "ollama"
    assert "url" in body
    assert "model" in body
    assert "healthy" in body
    assert isinstance(body["healthy"], bool)


@pytest.mark.anyio
async def test_run_now_endpoint(client, tenant):
    r = await client.post(
        "/api/v1/intel/admin/run-now", headers=TENANT_HEADERS
    )
    assert r.status_code == 202
    assert r.json().get("queued") is True


# ─── Multi-tenant isolation ─────────────────────────────────────────


@pytest.mark.anyio
async def test_targets_are_tenant_isolated(client, tenant):
    """A target created under 'go4energy' must NOT leak to another tenant."""
    r = await client.post(
        "/api/v1/intel/targets",
        json={"name": "g4-private", "kind": "competitor"},
        headers=TENANT_HEADERS,
    )
    assert r.status_code == 201
    target_name = r.json()["name"]

    # Create a second tenant + query as that tenant
    await client.post(
        "/api/v1/tenants",
        json={"tenant_id": "other-tenant", "tenant_name": "Other"},
    )
    other_headers = {**TEST_AUTH_HEADERS, "X-Tenant-ID": "other-tenant"}
    r = await client.get("/api/v1/intel/targets", headers=other_headers)
    assert r.status_code == 200
    other_names = [t["name"] for t in r.json()]
    assert target_name not in other_names
