"""Tests for Letter Module."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.letter.models import (
    BatchStatus,
    Letter,
    LetterBatch,
    LetterStatus,
    LetterTemplate,
)
from app.letter.schemas import RecipientData
from app.letter.service import LetterService

TENANT_ID = "test-tenant"


# ============== Fixtures ==============


@pytest_asyncio.fixture
async def letter_service(db_session: AsyncSession) -> LetterService:
    """Create LetterService instance."""
    return LetterService(db_session, TENANT_ID)


@pytest_asyncio.fixture
async def sample_template(db_session: AsyncSession) -> LetterTemplate:
    """Create a sample template."""
    template = LetterTemplate(
        tenant_id=TENANT_ID,
        name="Test Template",
        description="A test template",
        format="a4",
        content_html="<p>Sehr geehrte/r {{contact.name}},</p><p>Test content.</p>",
        header_html="<div>Header</div>",
        footer_html="<div>Footer</div>",
        is_active=True,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def sample_letter(
    db_session: AsyncSession, sample_template: LetterTemplate
) -> Letter:
    """Create a sample letter."""
    letter = Letter(
        tenant_id=TENANT_ID,
        template_id=sample_template.id,
        recipient_name="Max Mustermann",
        recipient_company="Test GmbH",
        recipient_street="Teststraße 1",
        recipient_zip="12345",
        recipient_city="Berlin",
        recipient_country="DE",
        content_html="<p>Rendered content</p>",
        status=LetterStatus.DRAFT,
    )
    db_session.add(letter)
    await db_session.commit()
    await db_session.refresh(letter)
    return letter


@pytest_asyncio.fixture
async def approved_letter(
    db_session: AsyncSession, sample_template: LetterTemplate
) -> Letter:
    """Create an approved letter."""
    letter = Letter(
        tenant_id=TENANT_ID,
        template_id=sample_template.id,
        recipient_name="Anna Schmidt",
        recipient_company="Schmidt AG",
        recipient_street="Hauptstraße 5",
        recipient_zip="80331",
        recipient_city="München",
        recipient_country="DE",
        content_html="<p>Approved content</p>",
        status=LetterStatus.APPROVED,
    )
    db_session.add(letter)
    await db_session.commit()
    await db_session.refresh(letter)
    return letter


# ============== Template Tests ==============


class TestTemplates:
    """Tests for template operations."""

    @pytest.mark.asyncio
    async def test_create_template(self, letter_service: LetterService):
        """Test creating a template."""
        template = await letter_service.create_template(
            name="New Template",
            content_html="<p>Content</p>",
            description="Description",
            format="a4",
        )

        assert template.id is not None
        assert template.name == "New Template"
        assert template.tenant_id == TENANT_ID
        assert template.is_active is True

    @pytest.mark.asyncio
    async def test_list_templates(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test listing templates."""
        templates, total = await letter_service.list_templates()

        assert total >= 1
        assert any(t.id == sample_template.id for t in templates)

    @pytest.mark.asyncio
    async def test_list_templates_active_only(
        self,
        letter_service: LetterService,
        sample_template: LetterTemplate,
        db_session: AsyncSession,
    ):
        """Test filtering active templates."""
        # Create inactive template
        inactive = LetterTemplate(
            tenant_id=TENANT_ID,
            name="Inactive",
            format="a4",
            content_html="<p>X</p>",
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        templates, total = await letter_service.list_templates(active_only=True)
        assert all(t.is_active for t in templates)

    @pytest.mark.asyncio
    async def test_get_template(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test getting a template by ID."""
        template = await letter_service.get_template(sample_template.id)

        assert template is not None
        assert template.id == sample_template.id
        assert template.name == sample_template.name

    @pytest.mark.asyncio
    async def test_update_template(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test updating a template."""
        template = await letter_service.update_template(
            sample_template.id, name="Updated Name", is_active=False
        )

        assert template.name == "Updated Name"
        assert template.is_active is False

    @pytest.mark.asyncio
    async def test_delete_template(
        self, letter_service: LetterService, db_session: AsyncSession
    ):
        """Test deleting (deactivating) a template."""
        template = LetterTemplate(
            tenant_id=TENANT_ID,
            name="To Delete",
            format="a4",
            content_html="<p>X</p>",
        )
        db_session.add(template)
        await db_session.commit()

        result = await letter_service.delete_template(template.id)
        assert result is True

        # Verify soft-deleted (deactivated)
        deleted = await letter_service.get_template(template.id)
        assert deleted is not None
        assert deleted.is_active is False


# ============== Letter Tests ==============


class TestLetters:
    """Tests for letter operations."""

    @pytest.mark.asyncio
    async def test_create_letter(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test creating a letter."""
        recipient = RecipientData(
            name="Hans Meier",
            company="Meier AG",
            street="Hauptstraße 10",
            zip="80331",
            city="München",
        )
        letter = await letter_service.create_letter(
            template_id=sample_template.id,
            recipient=recipient,
        )

        assert letter.id is not None
        assert letter.recipient_name == "Hans Meier"
        assert letter.status == LetterStatus.DRAFT

    @pytest.mark.asyncio
    async def test_list_letters(
        self, letter_service: LetterService, sample_letter: Letter
    ):
        """Test listing letters."""
        letters, total = await letter_service.list_letters()

        assert total >= 1
        assert any(letter.id == sample_letter.id for letter in letters)

    @pytest.mark.asyncio
    async def test_list_letters_by_status(
        self, letter_service: LetterService, sample_letter: Letter
    ):
        """Test filtering letters by status."""
        letters, total = await letter_service.list_letters(status="draft")

        assert all(letter.status == "draft" for letter in letters)

    @pytest.mark.asyncio
    async def test_get_letter(
        self, letter_service: LetterService, sample_letter: Letter
    ):
        """Test getting a letter by ID."""
        letter = await letter_service.get_letter(sample_letter.id)

        assert letter is not None
        assert letter.id == sample_letter.id
        assert letter.recipient_name == "Max Mustermann"

    @pytest.mark.asyncio
    async def test_approve_letter(
        self, letter_service: LetterService, sample_letter: Letter
    ):
        """Test approving a draft letter."""
        letter = await letter_service.approve_letter(sample_letter.id)

        assert letter is not None
        assert letter.status == LetterStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_non_draft_returns_none(
        self, letter_service: LetterService, approved_letter: Letter
    ):
        """Test approving an already approved letter returns None."""
        result = await letter_service.approve_letter(approved_letter.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_letter(
        self, letter_service: LetterService, sample_letter: Letter
    ):
        """Test deleting a draft letter."""
        result = await letter_service.delete_letter(sample_letter.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_non_draft_returns_false(
        self, letter_service: LetterService, approved_letter: Letter
    ):
        """Test that non-draft letters cannot be deleted."""
        result = await letter_service.delete_letter(approved_letter.id)
        assert result is False


# ============== Batch Tests ==============


class TestBatches:
    """Tests for batch operations."""

    @pytest.mark.asyncio
    async def test_create_batch(
        self,
        letter_service: LetterService,
        db_session: AsyncSession,
        sample_template: LetterTemplate,
    ):
        """Test creating a batch from approved letters."""
        letters = []
        for i in range(3):
            letter = Letter(
                tenant_id=TENANT_ID,
                template_id=sample_template.id,
                recipient_name=f"Person {i}",
                recipient_country="DE",
                content_html=f"<p>Content {i}</p>",
                status=LetterStatus.APPROVED,
            )
            db_session.add(letter)
            letters.append(letter)
        await db_session.commit()

        batch = await letter_service.create_batch(
            name="Test Batch",
            letter_ids=[letter.id for letter in letters],
        )

        assert batch.id is not None
        assert batch.name == "Test Batch"
        assert batch.letter_count == 3
        assert batch.status == BatchStatus.READY

    @pytest.mark.asyncio
    async def test_list_batches(
        self,
        letter_service: LetterService,
        db_session: AsyncSession,
    ):
        """Test listing batches."""
        batch = LetterBatch(
            tenant_id=TENANT_ID,
            name="List Test Batch",
            letter_count=0,
            status=BatchStatus.COLLECTING,
        )
        db_session.add(batch)
        await db_session.commit()

        batches, total = await letter_service.list_batches()

        assert total >= 1
        assert any(b.name == "List Test Batch" for b in batches)


# ============== Template Rendering Tests ==============


class TestTemplateRendering:
    """Tests for template rendering."""

    @pytest.mark.asyncio
    async def test_render_template_with_custom_data(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test template rendering with custom data."""
        html = await letter_service.render_template(
            sample_template,
            custom_data={
                "contact": {"name": "Test Person"},
            },
        )

        assert "Test Person" in html
        assert "{{contact.name}}" not in html

    @pytest.mark.asyncio
    async def test_render_template_without_data(
        self, letter_service: LetterService, sample_template: LetterTemplate
    ):
        """Test rendering fallback when no contact data."""
        html = await letter_service.render_template(sample_template)

        # Without contact data, Jinja renders empty or uses undefined
        assert html is not None


# ============== Stats Tests ==============


class TestStats:
    """Tests for statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        letter_service: LetterService,
        sample_template: LetterTemplate,
        sample_letter: Letter,
    ):
        """Test getting statistics."""
        stats = await letter_service.get_stats()

        assert stats["total_templates"] >= 1
        assert stats["total_letters"] >= 1
        assert isinstance(stats["letters_by_status"], dict)


# ============== API Endpoint Tests ==============


class TestAPIEndpoints:
    """Tests for API endpoints via HTTP client."""

    @pytest.mark.asyncio
    async def test_get_stats_endpoint(self, client):
        """Test stats endpoint."""
        response = await client.get(
            "/api/v1/letter/stats",
            headers={"X-Tenant-ID": TENANT_ID},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_templates" in data

    @pytest.mark.asyncio
    async def test_list_templates_endpoint(self, client):
        """Test list templates endpoint."""
        response = await client.get(
            "/api/v1/letter/templates",
            headers={"X-Tenant-ID": TENANT_ID},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_letters_endpoint(self, client):
        """Test list letters endpoint."""
        response = await client.get(
            "/api/v1/letter/letters",
            headers={"X-Tenant-ID": TENANT_ID},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_batches_endpoint(self, client):
        """Test list batches endpoint."""
        response = await client.get(
            "/api/v1/letter/batches",
            headers={"X-Tenant-ID": TENANT_ID},
        )
        assert response.status_code == 200
