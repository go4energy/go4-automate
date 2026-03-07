"""
Tests for Custom Audience Service

Tests the CustomAudienceService including:
- PII hashing for audiences
- Contact matching for segments
- Audience CRUD operations
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import all related models to ensure SQLAlchemy registry is properly configured
from app.contacts.models import Contact  # noqa: F401
from app.engagement.audience_service import CustomAudienceService
from app.engagement.meta_models import (  # noqa: F401
    AudienceSyncLog,
    CustomAudience,
    MetaIntegration,
    SyncMode,
)
from app.engagement.models import EngagementPipeline, PipelineEnrollment  # noqa: F401


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
    integration.ad_account_id = "987654321"
    integration.is_active = True
    return integration


@pytest.fixture
def audience_service(mock_db):
    """Create a CustomAudienceService instance."""
    return CustomAudienceService(mock_db, "test-tenant")


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ============== PII Hashing Tests ==============


class TestPIIHashing:
    """Tests for PII hashing according to Meta specification."""

    def test_hash_pii_basic(self, audience_service):
        """Test basic PII hashing."""
        result = audience_service.hash_pii("test@example.com")
        expected = hashlib.sha256("test@example.com".encode()).hexdigest()
        assert result == expected

    def test_hash_pii_lowercase(self, audience_service):
        """Test that hashing converts to lowercase."""
        result1 = audience_service.hash_pii("Test@Example.COM")
        result2 = audience_service.hash_pii("test@example.com")
        assert result1 == result2

    def test_hash_pii_trim(self, audience_service):
        """Test that hashing trims whitespace."""
        result1 = audience_service.hash_pii("  test@example.com  ")
        result2 = audience_service.hash_pii("test@example.com")
        assert result1 == result2

    def test_hash_pii_none(self, audience_service):
        """Test hashing of None value."""
        assert audience_service.hash_pii(None) == ""

    def test_hash_pii_empty(self, audience_service):
        """Test hashing of empty string."""
        assert audience_service.hash_pii("") == ""
        assert audience_service.hash_pii("   ") == ""


class TestPhoneNormalization:
    """Tests for phone number normalization."""

    def test_normalize_phone_basic(self, audience_service):
        """Test basic phone normalization."""
        result = audience_service.normalize_phone("+49 123 456789")
        assert result == "49123456789"

    def test_normalize_phone_with_leading_zero(self, audience_service):
        """Test German phone with leading zero."""
        result = audience_service.normalize_phone("0123 456789")
        assert result == "49123456789"

    def test_normalize_phone_special_chars(self, audience_service):
        """Test phone with special characters."""
        result = audience_service.normalize_phone("+49-123/456.789")
        assert result == "49123456789"

    def test_normalize_phone_none(self, audience_service):
        """Test normalization of None."""
        assert audience_service.normalize_phone(None) == ""

    def test_normalize_phone_empty(self, audience_service):
        """Test normalization of empty string."""
        assert audience_service.normalize_phone("") == ""


class TestHashContact:
    """Tests for contact hashing."""

    def test_hash_contact_full(self, audience_service, mock_contact):
        """Test hashing a contact with all fields."""
        result = audience_service.hash_contact(mock_contact)

        # Should be a list with 4 elements
        assert len(result) == 4

        # Email should be hashed (lowercase, trimmed)
        expected_email_hash = hashlib.sha256(b"test@example.com").hexdigest()
        assert result[0] == expected_email_hash

        # Phone should be normalized and hashed
        expected_phone_hash = hashlib.sha256(b"49123456789").hexdigest()
        assert result[1] == expected_phone_hash

        # First name should be hashed
        expected_fn_hash = hashlib.sha256(b"max").hexdigest()
        assert result[2] == expected_fn_hash

        # Last name should be hashed
        expected_ln_hash = hashlib.sha256(b"mustermann").hexdigest()
        assert result[3] == expected_ln_hash

    def test_hash_contact_partial(self, audience_service):
        """Test hashing a contact with partial fields."""
        contact = MagicMock()
        contact.id = 456
        contact.email = "only@email.com"
        contact.phone = None
        contact.first_name = None
        contact.last_name = None

        result = audience_service.hash_contact(contact)

        # Email should be hashed
        assert result[0] != ""
        # Others should be empty
        assert result[1] == ""
        assert result[2] == ""
        assert result[3] == ""

    def test_is_valid_contact_data_with_email(self, audience_service):
        """Test validation with email."""
        hashed_row = ["emailhash", "", "", ""]
        assert audience_service.is_valid_contact_data(hashed_row) is True

    def test_is_valid_contact_data_with_phone(self, audience_service):
        """Test validation with phone."""
        hashed_row = ["", "phonehash", "", ""]
        assert audience_service.is_valid_contact_data(hashed_row) is True

    def test_is_valid_contact_data_without_email_or_phone(self, audience_service):
        """Test validation without email or phone."""
        hashed_row = ["", "", "fnhash", "lnhash"]
        assert audience_service.is_valid_contact_data(hashed_row) is False


# ============== Sync Mode Constants Tests ==============


class TestSyncMode:
    """Tests for sync mode constants."""

    def test_sync_modes(self):
        """Test sync mode constants exist."""
        assert SyncMode.MANUAL == "manual"
        assert SyncMode.DAILY == "daily"
        assert SyncMode.REALTIME == "realtime"

    def test_all_sync_modes(self):
        """Test all() returns all modes."""
        all_modes = SyncMode.all()
        assert "manual" in all_modes
        assert "daily" in all_modes
        assert "realtime" in all_modes
        assert len(all_modes) == 3


# ============== Audience CRUD Tests ==============


class TestAudienceCRUD:
    """Tests for audience CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_audience_requires_integration(self, audience_service, mock_db):
        """Test that creating audience requires Meta integration."""
        # Mock no integration found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Meta integration not configured"):
            await audience_service.create_audience(
                name="Test Audience",
                description="Test description",
            )

    @pytest.mark.asyncio
    async def test_create_audience_requires_ad_account(
        self, audience_service, mock_db, mock_integration
    ):
        """Test that creating audience requires Ad Account ID."""
        mock_integration.ad_account_id = None

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_integration)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Ad Account ID not configured"):
            await audience_service.create_audience(name="Test Audience")

    @pytest.mark.asyncio
    async def test_update_audience_not_found(self, audience_service, mock_db):
        """Test updating non-existent audience raises error."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await audience_service.update_audience(999, name="New Name")

    @pytest.mark.asyncio
    async def test_delete_audience_not_found(self, audience_service, mock_db):
        """Test deleting non-existent audience raises error."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await audience_service.delete_audience(999)


# ============== Sync Tests ==============


class TestAudienceSync:
    """Tests for audience sync operations."""

    @pytest.mark.asyncio
    async def test_sync_audience_not_found(self, audience_service, mock_db):
        """Test syncing non-existent audience raises error."""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await audience_service.sync_audience(999)

    @pytest.mark.asyncio
    async def test_add_contact_to_audience_no_meta_audience(
        self, audience_service, mock_db
    ):
        """Test adding contact when audience has no Meta audience ID."""
        mock_audience = MagicMock()
        mock_audience.meta_audience_id = None

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_audience)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await audience_service.add_contact_to_audience(1, 123)
        assert result is False
