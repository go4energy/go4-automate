"""Distributor pipeline tests."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.distributor.hashing import hash_for_meta, hash_phone
from app.distributor.optimizer import (
    _calc_reduced_budget,
    _calc_scaled_budget,
    _calc_weather_budget,
)

HEADERS = {"X-Tenant-ID": "test-tenant"}


# --- Hashing Tests ---


def test_hash_for_meta_email():
    """hash_for_meta should lowercase, trim, and SHA256."""
    result = hash_for_meta("  Test@Example.COM  ")
    assert result is not None
    assert len(result) == 64
    # Same input should produce same hash
    assert result == hash_for_meta("test@example.com")


def test_hash_for_meta_none():
    """hash_for_meta with None should return None."""
    assert hash_for_meta(None) is None
    assert hash_for_meta("") is None


def test_hash_phone_with_country_code():
    """hash_phone should keep 49 prefix if already present."""
    result = hash_phone("491234567890")
    assert result is not None
    assert len(result) == 64


def test_hash_phone_without_country_code():
    """hash_phone should prepend 49 and strip leading 0."""
    r1 = hash_phone("01234567890")
    r2 = hash_phone("491234567890")
    assert r1 == r2


def test_hash_phone_none():
    """hash_phone with None should return None."""
    assert hash_phone(None) is None
    assert hash_phone("") is None


# --- Optimizer Budget Calculation Tests ---


def test_calc_reduced_budget():
    """Reduce should cut by 20%."""
    result = _calc_reduced_budget(Decimal("100.00"), None)
    assert result == Decimal("80.00")


def test_calc_reduced_budget_respects_minimum():
    """Reduce should not go below minimum."""
    result = _calc_reduced_budget(Decimal("15.00"), Decimal("14.00"))
    assert result == Decimal("14.00")


def test_calc_scaled_budget():
    """Scale should increase by 20%."""
    result = _calc_scaled_budget(Decimal("100.00"), None)
    assert result == Decimal("120.00")


def test_calc_scaled_budget_respects_maximum():
    """Scale should not exceed maximum."""
    result = _calc_scaled_budget(Decimal("90.00"), Decimal("100.00"))
    assert result == Decimal("100.00")


def test_calc_weather_budget():
    """Weather boost should multiply by factor."""
    result = _calc_weather_budget(Decimal("50.00"), Decimal("1.5"), None)
    assert result == Decimal("75.00")


def test_calc_weather_budget_respects_maximum():
    """Weather boost should not exceed maximum."""
    result = _calc_weather_budget(Decimal("80.00"), Decimal("1.5"), Decimal("100.00"))
    assert result == Decimal("100.00")


# --- Router / API Tests ---


@pytest.mark.anyio
async def test_track_conversion(client, test_tenant):
    """POST /api/v1/distributor/conversions should track a conversion event."""
    payload = {
        "event_name": "Lead",
        "event_time": "2026-02-17T10:00:00",
        "source_url": "https://example.com/form",
        "user_data": {
            "email": "test@example.com",
            "phone": "491234567890",
        },
    }
    response = await client.post(
        "/api/v1/distributor/conversions", json=payload, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_name"] == "Lead"
    assert data["tenant_id"] == "test-tenant"
    assert data["sent_to_meta"] is False


@pytest.mark.anyio
async def test_get_dashboard(client, test_tenant):
    """GET /api/v1/distributor/dashboard should return dashboard stats."""
    response = await client.get("/api/v1/distributor/dashboard", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "today" in data
    assert "this_week" in data
    assert "this_month" in data
    assert "trend" in data
    assert "campaigns" in data


@pytest.mark.anyio
async def test_get_performance_empty(client, test_tenant):
    """GET /api/v1/distributor/performance should return empty list when no data."""
    response = await client.get("/api/v1/distributor/performance", headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_create_campaign_config(client, test_tenant):
    """POST /api/v1/distributor/campaigns/config should create a campaign config."""
    payload = {
        "campaign_id": "23456789012345",
        "campaign_name": "Solar-Leads Wien",
        "target_cpl": "15.00",
        "max_cpl": "30.00",
        "daily_budget_min": "10.00",
        "daily_budget_max": "100.00",
        "weather_boost_enabled": True,
        "weather_boost_factor": "1.5",
        "auto_optimize": True,
    }
    response = await client.post(
        "/api/v1/distributor/campaigns/config", json=payload, headers=HEADERS
    )
    assert response.status_code == 201
    data = response.json()
    assert data["campaign_id"] == "23456789012345"
    assert data["campaign_name"] == "Solar-Leads Wien"
    assert data["status"] == "active"


@pytest.mark.anyio
async def test_list_campaigns(client, test_tenant):
    """GET /api/v1/distributor/campaigns should list campaign configs."""
    # Create two configs
    for name in ["Kampagne A", "Kampagne B"]:
        await client.post(
            "/api/v1/distributor/campaigns/config",
            json={"campaign_id": f"camp_{name}", "campaign_name": name},
            headers=HEADERS,
        )

    response = await client.get("/api/v1/distributor/campaigns", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_update_campaign_config(client, test_tenant):
    """PATCH /api/v1/distributor/campaigns/{id}/config should update a config."""
    create_resp = await client.post(
        "/api/v1/distributor/campaigns/config",
        json={"campaign_id": "camp_123", "campaign_name": "Original"},
        headers=HEADERS,
    )
    config_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/distributor/campaigns/{config_id}/config",
        json={"campaign_name": "Updated", "target_cpl": "20.00"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["campaign_name"] == "Updated"


@pytest.mark.anyio
async def test_duplicate_campaign_config(client, test_tenant):
    """Creating duplicate campaign config should return 400."""
    payload = {"campaign_id": "camp_dup", "campaign_name": "Test"}
    await client.post("/api/v1/distributor/campaigns/config", json=payload, headers=HEADERS)
    response = await client.post(
        "/api/v1/distributor/campaigns/config", json=payload, headers=HEADERS
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_pixel_snippet(client):
    """GET /api/v1/distributor/pixel-snippet should return pixel snippet."""
    with patch("app.distributor.router.settings") as mock_settings:
        mock_settings.meta_pixel_id = "123456789"
        mock_settings.domain = "example.com"
        response = await client.get("/api/v1/distributor/pixel-snippet")
        assert response.status_code == 200
        data = response.json()
        assert data["pixel_id"] == "123456789"
        assert "fbevents.js" in data["snippet"]
        assert "123456789" in data["snippet"]


@pytest.mark.anyio
@patch("app.distributor.service.get_current_weather", new_callable=AsyncMock)
async def test_weather_endpoint_no_key(mock_weather, client, test_tenant):
    """GET /api/v1/distributor/weather should fail when no API key configured."""
    response = await client.get("/api/v1/distributor/weather", headers=HEADERS)
    # No openweather_api_key configured -> 400
    assert response.status_code == 400
