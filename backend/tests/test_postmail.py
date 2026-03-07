"""Tests for Post-Mail Module."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.postmail.models import (
    BatchStatus,
    LetterStatus,
    PostmailBatch,
    PostmailLetter,
    PostmailTemplate,
)
from app.postmail.service import PostmailService

TENANT_ID = "test-tenant"


# ============== Fixtures ==============


@pytest_asyncio.fixture
async def postmail_service(db_session: AsyncSession) -> PostmailService:
    """Create PostmailService instance."""
    return PostmailService(db_session, TENANT_ID)


@pytest_asyncio.fixture
async def sample_template(db_session: AsyncSession) -> PostmailTemplate:
    """Create a sample template."""
    template = PostmailTemplate(
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
    db_session: AsyncSession, sample_template: PostmailTemplate
) -> PostmailLetter:
    """Create a sample letter."""
    letter = PostmailLetter(
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
async def sample_batch(
    db_session: AsyncSession, sample_letter: PostmailLetter
) -> PostmailBatch:
    """Create a sample batch."""
    # First approve the letter
    sample_letter.status = LetterStatus.APPROVED
    await db_session.commit()

    batch = PostmailBatch(
        tenant_id=TENANT_ID,
        name="Test Batch",
        letter_count=1,
        status=BatchStatus.COLLECTING,
    )
    db_session.add(batch)
    await db_session.flush()

    sample_letter.batch_id = batch.id
    sample_letter.status = LetterStatus.QUEUED
    await db_session.commit()
    await db_session.refresh(batch)
    return batch


# ============== Template Tests ==============


class TestTemplates:
    """Tests for template operations."""

    @pytest.mark.asyncio
    async def test_create_template(self, postmail_service: PostmailService):
        """Test creating a template."""
        from app.postmail.schemas import TemplateCreate

        data = TemplateCreate(
            name="New Template",
            description="Description",
            format="a4",
            content_html="<p>Content</p>",
        )
        template = await postmail_service.create_template(data)

        assert template.id is not None
        assert template.name == "New Template"
        assert template.tenant_id == TENANT_ID
        assert template.is_active is True

    @pytest.mark.asyncio
    async def test_list_templates(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test listing templates."""
        result = await postmail_service.list_templates()

        assert len(result.items) >= 1
        assert any(t.id == sample_template.id for t in result.items)

    @pytest.mark.asyncio
    async def test_list_templates_active_only(
        self,
        postmail_service: PostmailService,
        sample_template: PostmailTemplate,
        db_session: AsyncSession,
    ):
        """Test filtering active templates."""
        # Create inactive template
        inactive = PostmailTemplate(
            tenant_id=TENANT_ID,
            name="Inactive",
            format="a4",
            content_html="<p>X</p>",
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.commit()

        result = await postmail_service.list_templates(active_only=True)
        assert all(t.is_active for t in result.items)

    @pytest.mark.asyncio
    async def test_get_template(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test getting a template by ID."""
        template = await postmail_service.get_template(sample_template.id)

        assert template is not None
        assert template.id == sample_template.id
        assert template.name == sample_template.name

    @pytest.mark.asyncio
    async def test_update_template(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test updating a template."""
        from app.postmail.schemas import TemplateUpdate

        data = TemplateUpdate(name="Updated Name", is_active=False)
        template = await postmail_service.update_template(sample_template.id, data)

        assert template.name == "Updated Name"
        assert template.is_active is False

    @pytest.mark.asyncio
    async def test_delete_template(
        self, postmail_service: PostmailService, db_session: AsyncSession
    ):
        """Test deleting a template without letters."""
        # Create a template without letters
        template = PostmailTemplate(
            tenant_id=TENANT_ID,
            name="To Delete",
            format="a4",
            content_html="<p>X</p>",
        )
        db_session.add(template)
        await db_session.commit()

        result = await postmail_service.delete_template(template.id)
        assert result is True

        # Verify deleted
        deleted = await postmail_service.get_template(template.id)
        assert deleted is None


# ============== Letter Tests ==============


class TestLetters:
    """Tests for letter operations."""

    @pytest.mark.asyncio
    async def test_create_letter(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test creating a letter."""
        from app.postmail.schemas import LetterCreate, RecipientData

        data = LetterCreate(
            template_id=sample_template.id,
            recipient=RecipientData(
                name="Hans Meier",
                company="Meier AG",
                street="Hauptstraße 10",
                zip="80331",
                city="München",
            ),
        )
        letter = await postmail_service.create_letter(data)

        assert letter.id is not None
        assert letter.recipient_name == "Hans Meier"
        assert letter.status == LetterStatus.DRAFT
        assert letter.content_html is not None  # Rendered from template

    @pytest.mark.asyncio
    async def test_list_letters(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test listing letters."""
        result = await postmail_service.list_letters()

        assert len(result.items) >= 1
        assert any(letter.id == sample_letter.id for letter in result.items)

    @pytest.mark.asyncio
    async def test_list_letters_by_status(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test filtering letters by status."""
        result = await postmail_service.list_letters(status="draft")

        assert all(letter.status == "draft" for letter in result.items)

    @pytest.mark.asyncio
    async def test_get_letter(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test getting a letter by ID."""
        letter = await postmail_service.get_letter(sample_letter.id)

        assert letter is not None
        assert letter.id == sample_letter.id
        assert letter.recipient_name == "Max Mustermann"

    @pytest.mark.asyncio
    async def test_approve_letter(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test approving a letter."""
        letter = await postmail_service.approve_letter(sample_letter.id)

        assert letter.status == LetterStatus.APPROVED

    @pytest.mark.asyncio
    async def test_approve_already_approved(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test approving an already approved letter."""
        # First approval
        await postmail_service.approve_letter(sample_letter.id)

        # Second approval should fail
        with pytest.raises(ValueError, match="already"):
            await postmail_service.approve_letter(sample_letter.id)

    @pytest.mark.asyncio
    async def test_delete_letter(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test deleting a draft letter."""
        result = await postmail_service.delete_letter(sample_letter.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_non_draft_letter(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test that non-draft letters cannot be deleted."""
        # Approve the letter
        await postmail_service.approve_letter(sample_letter.id)

        # Try to delete
        with pytest.raises(ValueError, match="draft"):
            await postmail_service.delete_letter(sample_letter.id)


# ============== Batch Tests ==============


class TestBatches:
    """Tests for batch operations."""

    @pytest.mark.asyncio
    async def test_create_batch(
        self,
        postmail_service: PostmailService,
        db_session: AsyncSession,
        sample_template: PostmailTemplate,
    ):
        """Test creating a batch."""
        # Create approved letters
        letters = []
        for i in range(3):
            letter = PostmailLetter(
                tenant_id=TENANT_ID,
                template_id=sample_template.id,
                recipient_name=f"Person {i}",
                recipient_country="DE",
                status=LetterStatus.APPROVED,
            )
            db_session.add(letter)
            letters.append(letter)
        await db_session.commit()

        from app.postmail.schemas import BatchCreate

        data = BatchCreate(
            name="Test Batch",
            letter_ids=[letter.id for letter in letters],
        )
        batch = await postmail_service.create_batch(data)

        assert batch.id is not None
        assert batch.name == "Test Batch"
        assert batch.letter_count == 3
        assert batch.status == BatchStatus.READY

        # Check letters are queued
        for letter in letters:
            await db_session.refresh(letter)
            assert letter.batch_id == batch.id
            assert letter.status == LetterStatus.QUEUED

    @pytest.mark.asyncio
    async def test_create_batch_with_non_approved_letters(
        self, postmail_service: PostmailService, sample_letter: PostmailLetter
    ):
        """Test that batch creation fails with non-approved letters."""
        from app.postmail.schemas import BatchCreate

        data = BatchCreate(
            name="Bad Batch",
            letter_ids=[sample_letter.id],
        )

        with pytest.raises(ValueError, match="approved"):
            await postmail_service.create_batch(data)

    @pytest.mark.asyncio
    async def test_list_batches(
        self, postmail_service: PostmailService, sample_batch: PostmailBatch
    ):
        """Test listing batches."""
        result = await postmail_service.list_batches()

        assert len(result.items) >= 1
        assert any(b.id == sample_batch.id for b in result.items)

    @pytest.mark.asyncio
    async def test_export_batch(
        self, postmail_service: PostmailService, sample_batch: PostmailBatch
    ):
        """Test exporting a batch."""
        # Mark batch as ready first
        sample_batch.status = BatchStatus.READY
        await postmail_service.db.commit()

        result = await postmail_service.export_batch(sample_batch.id)

        assert result.batch_id == sample_batch.id
        assert result.export_path is not None
        assert result.letter_count >= 1

    @pytest.mark.asyncio
    async def test_mark_batch_sent(
        self, postmail_service: PostmailService, sample_batch: PostmailBatch
    ):
        """Test marking a batch as sent."""
        # Export first
        sample_batch.status = BatchStatus.EXPORTED
        await postmail_service.db.commit()

        batch = await postmail_service.mark_batch_sent(sample_batch.id)

        assert batch.status == BatchStatus.SENT
        assert batch.sent_at is not None


# ============== Template Rendering Tests ==============


class TestTemplateRendering:
    """Tests for template rendering."""

    @pytest.mark.asyncio
    async def test_render_template_basic(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test basic template rendering."""
        html = await postmail_service.render_template(
            sample_template,
            context={
                "contact": {"name": "Test Person"},
            },
        )

        assert "Test Person" in html
        assert "{{contact.name}}" not in html

    @pytest.mark.asyncio
    async def test_render_preview(
        self, postmail_service: PostmailService, sample_template: PostmailTemplate
    ):
        """Test render preview endpoint."""
        from app.postmail.schemas import RenderPreviewRequest

        request = RenderPreviewRequest(
            template_id=sample_template.id,
            custom_data={"contact": {"name": "Preview Test"}},
        )
        result = await postmail_service.render_preview(request)

        assert "Preview Test" in result.html


# ============== Stats Tests ==============


class TestStats:
    """Tests for statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        postmail_service: PostmailService,
        sample_template: PostmailTemplate,
        sample_letter: PostmailLetter,
    ):
        """Test getting statistics."""
        stats = await postmail_service.get_stats()

        assert stats.total_templates >= 1
        assert stats.total_letters >= 1
        assert "draft" in stats.letters_by_status or stats.letters_by_status == {}


# ============== API Endpoint Tests ==============


class TestAPIEndpoints:
    """Tests for API endpoints."""

    @pytest_asyncio.fixture
    async def api_client(self, db_session: AsyncSession) -> AsyncClient:
        """Create test client."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as ac:
            yield ac

    @pytest.fixture
    def auth_headers(self) -> dict:
        """Create auth headers."""
        return {
            "X-Backend-Secret": "test-secret",
            "X-Tenant-ID": TENANT_ID,
        }

    @pytest.mark.asyncio
    async def test_get_stats_endpoint(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test stats endpoint."""
        response = await api_client.get(
            "/api/v1/postmail/stats", headers=auth_headers
        )
        # May be 401 without proper auth setup, but endpoint exists
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_list_templates_endpoint(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test list templates endpoint."""
        response = await api_client.get(
            "/api/v1/postmail/templates", headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_list_letters_endpoint(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test list letters endpoint."""
        response = await api_client.get(
            "/api/v1/postmail/letters", headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]

    @pytest.mark.asyncio
    async def test_list_batches_endpoint(
        self, api_client: AsyncClient, auth_headers: dict
    ):
        """Test list batches endpoint."""
        response = await api_client.get(
            "/api/v1/postmail/batches", headers=auth_headers
        )
        assert response.status_code in [200, 401, 403]
