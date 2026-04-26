"""Tests for per-tenant module licensing."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

HEADERS = {"X-Tenant-ID": "go4energy"}


@pytest.mark.anyio
async def test_permissive_default_for_new_tenant(db_session):
    """A tenant with zero license rows is treated as having access to
    every module (legacy / un-licensed mode)."""
    from app.licensing.service import LicensingService

    service = LicensingService(db_session)
    enabled = await service.enabled_modules("go4energy")
    assert enabled == {"*"}
    assert await service.has_access("go4energy", "leadgen") is True
    assert await service.has_access("go4energy", "any-future-module") is True


@pytest.mark.anyio
async def test_grant_flips_to_restrictive(db_session):
    """Once any license row exists, only listed modules + CORE are allowed."""
    from app.licensing.service import CORE_MODULES, LicensingService

    service = LicensingService(db_session)
    await service.grant("go4energy", "leadgen", plan_tier="growth")
    await db_session.flush()

    enabled = await service.enabled_modules("go4energy")
    assert "leadgen" in enabled
    # Core is always present even without explicit grant
    assert CORE_MODULES.issubset(enabled)
    # Non-licensed module is now blocked
    assert await service.has_access("go4energy", "engagement") is False
    assert await service.has_access("go4energy", "leadgen") is True
    # Core module always passes
    assert await service.has_access("go4energy", "contacts") is True


@pytest.mark.anyio
async def test_grant_is_idempotent(db_session):
    """Re-granting the same module updates the row instead of duplicating."""
    from sqlalchemy import select

    from app.licensing.models import TenantModuleLicense
    from app.licensing.service import LicensingService

    service = LicensingService(db_session)
    first = await service.grant(
        "go4energy", "leadgen", plan_tier="trial",
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    second = await service.grant(
        "go4energy", "leadgen", plan_tier="growth", expires_at=None,
    )
    assert first.id == second.id  # same row mutated
    assert second.plan_tier == "growth"
    assert second.expires_at is None

    rows = (
        await db_session.execute(
            select(TenantModuleLicense).where(
                TenantModuleLicense.tenant_id == "go4energy",
                TenantModuleLicense.module_key == "leadgen",
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.anyio
async def test_expired_license_not_active(db_session):
    """Module with expires_at in the past loses access."""
    from app.licensing.service import LicensingService

    service = LicensingService(db_session)
    await service.grant(
        "go4energy", "leadgen",
        plan_tier="trial",
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    await db_session.flush()
    assert await service.has_access("go4energy", "leadgen") is False


@pytest.mark.anyio
async def test_revoke_removes_access(db_session):
    """Revoking the only license keeps the table empty → permissive."""
    from app.licensing.service import LicensingService

    service = LicensingService(db_session)
    await service.grant("go4energy", "leadgen")
    assert await service.has_access("go4energy", "leadgen") is True
    revoked = await service.revoke("go4energy", "leadgen")
    assert revoked is True
    # Revoking the only row → tenant is back in permissive mode
    enabled = await service.enabled_modules("go4energy")
    assert enabled == {"*"}


@pytest.mark.anyio
async def test_require_module_dependency_passes_in_permissive(db_session, client):
    """Endpoint guarded by require_module() should be reachable when the
    tenant has no license rows (permissive default). Sanity check via
    /api/v1/licensing/enabled which itself is a working endpoint."""
    resp = await client.get("/api/v1/licensing/enabled", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["permissive"] is True
    assert body["enabled"] == ["*"]


@pytest.mark.anyio
async def test_grant_via_api_persists(db_session, client):
    grant_resp = await client.post(
        "/api/v1/licensing/licenses",
        headers=HEADERS,
        json={"module_key": "leadgen", "plan_tier": "growth"},
    )
    assert grant_resp.status_code == 201
    body = grant_resp.json()
    assert body["module_key"] == "leadgen"
    assert body["plan_tier"] == "growth"
    assert body["is_active"] is True

    listing = await client.get("/api/v1/licensing/enabled", headers=HEADERS)
    enabled = listing.json()
    assert enabled["permissive"] is False
    assert "leadgen" in enabled["enabled"]
    # Core modules always show up
    assert "contacts" in enabled["enabled"]


@pytest.mark.anyio
async def test_revoke_via_api(db_session, client):
    await client.post(
        "/api/v1/licensing/licenses",
        headers=HEADERS,
        json={"module_key": "leadgen"},
    )
    revoke = await client.delete(
        "/api/v1/licensing/licenses/leadgen", headers=HEADERS
    )
    assert revoke.status_code == 204

    revoke_again = await client.delete(
        "/api/v1/licensing/licenses/leadgen", headers=HEADERS
    )
    assert revoke_again.status_code == 404
