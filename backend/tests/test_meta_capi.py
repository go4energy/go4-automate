"""
Tests for Meta Conversions API Integration

Tests the MetaConversionsService including:
- PII hashing
- Event payload building
- Integration CRUD
- Event logging
"""

import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from app.engagement.meta_models import ConversionEvent, MetaEventName, MetaIntegration
from app.engagement.meta_service import MetaConversionsService


# ============== Fixtures ==============


@pytest.fixture
def mock_contact():
    """Create a mock contact for testing."""
    contact = MagicMock()
    contact.id = 123
    contact.email = "Test@Example.com "  # With space and uppercase
    contact.phone = "+49 123 456 789"
    contact.first_name = "Max"
    contact.last_name = "Mustermann"
    return contact


@pytest.fixture
def mock_integration():
    """Create a mock Meta integration."""
    integration = MagicMock(spec=MetaIntegration)
    integration.id = 1
    integration.tenant_id = "test-tenant"
    integration.pixel_id = "1234567890123456"
    integration.access_token = "EAAxxxxxxxxxx"
    integration.test_mode = False
    integration.is_active = True
    integration.total_events_sent = 0
    integration.total_events_failed = 0
    return integration


@pytest.fixture
def meta_service(mock_db):
    """Create a MetaConversionsService instance."""
    return MetaConversionsService(mock_db, "test-tenant")


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ============== PII Hashing Tests ==============


class TestPIIHashing:
    """Tests for PII hashing according to Meta specification."""

    def test_hash_pii_basic(self, meta_service):
        """Test basic PII hashing."""
        result = meta_service.hash_pii("test@example.com")
        expected = hashlib.sha256("test@example.com".encode()).hexdigest()
        assert result == expected

    def test_hash_pii_lowercase(self, meta_service):
        """Test that hashing converts to lowercase."""
        result1 = meta_service.hash_pii("Test@Example.COM")
        result2 = meta_service.hash_pii("test@example.com")
        assert result1 == result2

    def test_hash_pii_trim(self, meta_service):
        """Test that hashing trims whitespace."""
        result1 = meta_service.hash_pii("  test@example.com  ")
        result2 = meta_service.hash_pii("test@example.com")
        assert result1 == result2

    def test_hash_pii_none(self, meta_service):
        """Test hashing of None value."""
        assert meta_service.hash_pii(None) is None

    def test_hash_pii_empty(self, meta_service):
        """Test hashing of empty string."""
        assert meta_service.hash_pii("") is None
        assert meta_service.hash_pii("   ") is None


class TestPhoneNormalization:
    """Tests for phone number normalization."""

    def test_normalize_phone_basic(self, meta_service):
        """Test basic phone normalization."""
        result = meta_service.normalize_phone("+49 123 456789")
        assert result == "49123456789"

    def test_normalize_phone_with_leading_zero(self, meta_service):
        """Test German phone with leading zero."""
        result = meta_service.normalize_phone("0123 456789")
        assert result == "49123456789"

    def test_normalize_phone_special_chars(self, meta_service):
        """Test phone with special characters."""
        result = meta_service.normalize_phone("+49-123/456.789")
        assert result == "49123456789"

    def test_normalize_phone_none(self, meta_service):
        """Test normalization of None."""
        assert meta_service.normalize_phone(None) is None

    def test_normalize_phone_empty(self, meta_service):
        """Test normalization of empty string."""
        assert meta_service.normalize_phone("") is None


# ============== User Data Building Tests ==============


class TestBuildUserData:
    """Tests for building user_data payload."""

    def test_build_user_data_full(self, meta_service, mock_contact):
        """Test building user_data with all fields."""
        result = meta_service.build_user_data(mock_contact)

        # Check all fields are present
        assert "em" in result
        assert "ph" in result
        assert "fn" in result
        assert "ln" in result
        assert "external_id" in result

        # Check values are arrays
        assert isinstance(result["em"], list)
        assert len(result["em"]) == 1

        # Check email is hashed correctly (lowercase, trimmed)
        expected_email_hash = hashlib.sha256("test@example.com".encode()).hexdigest()
        assert result["em"][0] == expected_email_hash

        # Check external_id is contact ID
        assert result["external_id"] == ["123"]

    def test_build_user_data_partial(self, meta_service):
        """Test building user_data with partial fields."""
        contact = MagicMock()
        contact.id = 456
        contact.email = "only@email.com"
        contact.phone = None
        contact.first_name = None
        contact.last_name = None

        result = meta_service.build_user_data(contact)

        assert "em" in result
        assert "ph" not in result
        assert "fn" not in result
        assert "ln" not in result
        assert "external_id" in result

    def test_get_user_data_fields(self, meta_service, mock_contact):
        """Test getting list of populated fields."""
        user_data = meta_service.build_user_data(mock_contact)
        fields = meta_service.get_user_data_fields(user_data)

        assert "em" in fields
        assert "ph" in fields
        assert "fn" in fields
        assert "ln" in fields
        assert "external_id" in fields


# ============== Event ID Generation Tests ==============


class TestEventIdGeneration:
    """Tests for event ID generation."""

    def test_generate_event_id(self, meta_service):
        """Test event ID format."""
        event_time = datetime(2024, 1, 15, 12, 30, 45)
        result = meta_service._generate_event_id(123, "PageView", event_time)

        expected_timestamp = int(event_time.timestamp())
        assert result == f"123_PageView_{expected_timestamp}"

    def test_event_id_unique(self, meta_service):
        """Test that different timestamps produce different IDs."""
        time1 = datetime(2024, 1, 15, 12, 30, 45)
        time2 = datetime(2024, 1, 15, 12, 30, 46)

        id1 = meta_service._generate_event_id(123, "PageView", time1)
        id2 = meta_service._generate_event_id(123, "PageView", time2)

        assert id1 != id2


# ============== Integration Tests ==============


class TestIntegrationManagement:
    """Tests for Meta integration CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_integration_valid(self, meta_service, mock_db):
        """Test creating a valid integration."""
        # Mock no existing integration
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        integration = await meta_service.create_integration(
            pixel_id="1234567890123456",
            access_token="EAAtest123",
            test_mode=True,
        )

        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_create_integration_invalid_pixel_id(self, meta_service):
        """Test that invalid pixel ID raises error."""
        with pytest.raises(ValueError, match="Pixel ID must be 15-16 digits"):
            await meta_service.create_integration(
                pixel_id="invalid",
                access_token="EAAtest123",
            )

    @pytest.mark.asyncio
    async def test_create_integration_short_pixel_id(self, meta_service):
        """Test that short pixel ID raises error."""
        with pytest.raises(ValueError, match="Pixel ID must be 15-16 digits"):
            await meta_service.create_integration(
                pixel_id="12345",
                access_token="EAAtest123",
            )


# ============== Event Constants Tests ==============


class TestMetaEventName:
    """Tests for event name constants."""

    def test_standard_events(self):
        """Test standard event names exist."""
        assert MetaEventName.PAGE_VIEW == "PageView"
        assert MetaEventName.LEAD == "Lead"
        assert MetaEventName.CONTACT == "Contact"
        assert MetaEventName.PURCHASE == "Purchase"

    def test_all_events(self):
        """Test all() returns all events."""
        all_events = MetaEventName.all()
        assert "PageView" in all_events
        assert "Lead" in all_events
        assert "Purchase" in all_events
        assert len(all_events) >= 10


# ============== Send Event Tests ==============


class TestSendEvent:
    """Tests for sending events to Meta."""

    @pytest.mark.asyncio
    async def test_send_event_no_integration(self, meta_service, mock_contact, mock_db):
        """Test that sending without integration returns None."""
        # Mock no integration found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await meta_service.send_event(
            event_name="PageView",
            contact=mock_contact,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_send_event_success(self, meta_service, mock_contact, mock_db, mock_integration):
        """Test successful event sending."""
        # Mock integration found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_integration)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock HTTP response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"events_received": 1}

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await meta_service.send_event(
                event_name="PageView",
                contact=mock_contact,
                event_source_url="https://example.com",
            )

            # Should return event_id
            assert result is not None
            assert "123_PageView_" in result

    @pytest.mark.asyncio
    async def test_send_event_failure(self, meta_service, mock_contact, mock_db, mock_integration):
        """Test failed event sending."""
        # Mock integration found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_integration)
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Mock HTTP error response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.content = b'{"error": {"message": "Invalid pixel"}}'
            mock_response.json.return_value = {"error": {"message": "Invalid pixel"}}

            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await meta_service.send_event(
                event_name="PageView",
                contact=mock_contact,
            )

            # Should return None on failure
            assert result is None


# ============== Convenience Method Tests ==============


class TestConvenienceMethods:
    """Tests for convenience tracking methods."""

    @pytest.mark.asyncio
    async def test_track_page_view_calls_send_event(self, meta_service, mock_contact):
        """Test track_page_view calls send_event correctly."""
        with patch.object(meta_service, "send_event", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = "test_event_id"

            await meta_service.track_page_view(
                contact=mock_contact,
                url="https://example.com/page",
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["event_name"] == "PageView"
            assert call_args.kwargs["event_source_url"] == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_track_lead_calls_send_event(self, meta_service, mock_contact):
        """Test track_lead calls send_event correctly."""
        with patch.object(meta_service, "send_event", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = "test_event_id"

            await meta_service.track_lead(
                contact=mock_contact,
                pipeline_name="Solar KMU",
                pipeline_id=1,
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["event_name"] == "Lead"
            assert call_args.kwargs["custom_data"]["content_name"] == "Solar KMU"

    @pytest.mark.asyncio
    async def test_track_conversion_calls_send_event(self, meta_service, mock_contact):
        """Test track_conversion calls send_event correctly."""
        with patch.object(meta_service, "send_event", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = "test_event_id"

            await meta_service.track_conversion(
                contact=mock_contact,
                value=5000.0,
                currency="EUR",
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["event_name"] == "Purchase"
            assert call_args.kwargs["custom_data"]["value"] == 5000.0
            assert call_args.kwargs["custom_data"]["currency"] == "EUR"
