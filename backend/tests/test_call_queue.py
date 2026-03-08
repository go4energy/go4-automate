"""Tests for CRM Call Queue integration."""

import pytest
from datetime import datetime, UTC


class TestCallQueueSchemas:
    """Test call queue schema validation."""

    def test_call_log_request_valid(self):
        from app.crm.schemas import CallLogRequest

        data = CallLogRequest(
            outcome="answered",
            duration_seconds=120,
            notes="Gutes Gespräch",
        )
        assert data.outcome == "answered"
        assert data.duration_seconds == 120

    def test_call_log_request_invalid_outcome(self):
        from app.crm.schemas import CallLogRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CallLogRequest(outcome="invalid_outcome")

    def test_call_log_request_all_outcomes(self):
        from app.crm.schemas import CallLogRequest

        valid_outcomes = [
            "answered", "no_answer", "voicemail", "wrong_number",
            "callback", "not_interested", "qualified",
        ]
        for outcome in valid_outcomes:
            data = CallLogRequest(outcome=outcome)
            assert data.outcome == outcome

    def test_call_stats_response_defaults(self):
        from app.crm.schemas import CallStatsResponse

        stats = CallStatsResponse()
        assert stats.total_pending == 0
        assert stats.due_today == 0
        assert stats.overdue == 0
        assert stats.completed_today == 0
        assert stats.by_priority == {}

    def test_call_action_response(self):
        from app.crm.schemas import CallActionResponse

        action = CallActionResponse(
            id=1,
            action_type="schedule_call",
            priority="high",
            status="pending",
            created_at=datetime.now(UTC),
            contact_name="Max Mustermann",
            contact_phone="+49 123 456",
            pipeline_name="Solar KMU",
        )
        assert action.contact_name == "Max Mustermann"
        assert action.pipeline_name == "Solar KMU"

    def test_call_log_with_follow_up(self):
        from datetime import date
        from app.crm.schemas import CallLogRequest

        data = CallLogRequest(
            outcome="callback",
            duration_seconds=60,
            notes="Rückruf nächste Woche",
            follow_up_date=date(2026, 3, 14),
            deal_id=42,
        )
        assert data.follow_up_date == date(2026, 3, 14)
        assert data.deal_id == 42


class TestCallQueueEndpoints:
    """Test call queue API endpoints using conftest client."""

    @pytest.mark.asyncio
    async def test_list_calls_endpoint(self, client, test_tenant):
        """Test GET /crm/calls returns 200."""
        response = await client.get(
            "/api/v1/crm/calls",
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_call_stats_endpoint(self, client, test_tenant):
        """Test GET /crm/calls/stats returns 200."""
        response = await client.get(
            "/api/v1/crm/calls/stats",
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_pending"] == 0
        assert data["due_today"] == 0
        assert data["overdue"] == 0
        assert data["completed_today"] == 0

    @pytest.mark.asyncio
    async def test_generate_script_not_found(self, client, test_tenant):
        """Test POST /crm/calls/999999/generate-script returns 404."""
        response = await client.post(
            "/api/v1/crm/calls/999999/generate-script",
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_log_call_not_found(self, client, test_tenant):
        """Test POST /crm/calls/999999/log returns 404."""
        response = await client.post(
            "/api/v1/crm/calls/999999/log",
            json={"outcome": "answered", "notes": "Test"},
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_log_call_invalid_outcome(self, client, test_tenant):
        """Test POST /crm/calls/1/log with invalid outcome returns 422."""
        response = await client.post(
            "/api/v1/crm/calls/1/log",
            json={"outcome": "invalid"},
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_calls_empty_result(self, client, test_tenant):
        """Test empty call queue returns empty list."""
        response = await client.get(
            "/api/v1/crm/calls",
            headers={"X-Tenant-ID": "test-tenant"},
        )
        assert response.status_code == 200
        assert response.json() == []
