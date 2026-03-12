"""Tests for LinkedIn outreach services - templates, campaigns, safety."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.linkedin.campaign_service import CampaignService
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInMessageTemplate,
)
from app.linkedin.outreach_service import TemplateService
from app.linkedin.safety_service import SafetyService
from app.linkedin.schemas import (
    LinkedInCampaignCreate,
    LinkedInCampaignLeadCreate,
    LinkedInCampaignStepCreate,
    LinkedInTemplateCreate,
    LinkedInTemplateUpdate,
)

# Mark all tests as anyio (uses asyncio backend per conftest.py)
pytestmark = pytest.mark.anyio


# ============== Fixtures ==============


@pytest.fixture
def tenant_id():
    return "test_tenant"


@pytest.fixture
async def linkedin_account(db_session: AsyncSession, tenant_id: str) -> LinkedInAccount:
    """Create a test LinkedIn account."""
    account = LinkedInAccount(
        tenant_id=tenant_id,
        name="Test Account",
        email="test@example.com",
        status="active",
        is_sales_navigator=True,
        daily_connection_limit=25,
        daily_message_limit=50,
        daily_profile_limit=100,
        warmup_enabled=False,
        warmup_day=14,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def warmup_account(db_session: AsyncSession, tenant_id: str) -> LinkedInAccount:
    """Create a test LinkedIn account in warmup phase."""
    account = LinkedInAccount(
        tenant_id=tenant_id,
        name="Warmup Account",
        email="warmup@example.com",
        status="warmup",
        is_sales_navigator=True,
        daily_connection_limit=25,
        daily_message_limit=50,
        daily_profile_limit=100,
        warmup_enabled=True,
        warmup_day=3,
        warmup_started_at=datetime.utcnow() - timedelta(days=3),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest.fixture
async def message_template(db_session: AsyncSession, tenant_id: str) -> LinkedInMessageTemplate:
    """Create a test message template."""
    template = LinkedInMessageTemplate(
        tenant_id=tenant_id,
        name="Test Template",
        category="message",
        content="Hello {first_name}, I saw you work at {company}. Let's connect!",
        variables=["first_name", "company"],
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


# ============== Template Service Tests ==============


async def test_create_template(db_session: AsyncSession, tenant_id: str):
    """Test creating a message template."""
    service = TemplateService(db_session)
    data = LinkedInTemplateCreate(
        name="New Template",
        category="connection_request",
        content="Hi {first_name}!",
    )

    template = await service.create(tenant_id, data)

    assert template.id is not None
    assert template.name == "New Template"
    assert template.category == "connection_request"
    assert "{first_name}" in template.content


async def test_render_template(
    db_session: AsyncSession, tenant_id: str, message_template: LinkedInMessageTemplate
):
    """Test rendering a template with variables."""
    service = TemplateService(db_session)

    context = {
        "first_name": "Max",
        "company": "Acme Corp",
    }
    # render() returns (content, subject) tuple
    rendered_content, rendered_subject = await service.render(tenant_id, message_template.id, context)

    assert "Max" in rendered_content
    assert "Acme Corp" in rendered_content
    assert "{first_name}" not in rendered_content


async def test_list_templates(
    db_session: AsyncSession, tenant_id: str, message_template: LinkedInMessageTemplate
):
    """Test listing templates."""
    service = TemplateService(db_session)

    templates = await service.list_templates(tenant_id)

    assert len(templates) >= 1
    assert any(t.id == message_template.id for t in templates)


async def test_update_template(
    db_session: AsyncSession, tenant_id: str, message_template: LinkedInMessageTemplate
):
    """Test updating a template."""
    service = TemplateService(db_session)

    update_data = LinkedInTemplateUpdate(name="Updated Template")
    updated = await service.update(tenant_id, message_template.id, update_data)

    assert updated.name == "Updated Template"


async def test_delete_template(
    db_session: AsyncSession, tenant_id: str, message_template: LinkedInMessageTemplate
):
    """Test deleting a template (soft delete)."""
    service = TemplateService(db_session)

    await service.delete(tenant_id, message_template.id)
    await db_session.refresh(message_template)

    # Verify soft-deleted (is_active set to False)
    assert message_template.is_active is False


# ============== Safety Service Tests ==============


async def test_can_perform_action_active_account(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test action allowed for active account within limits."""
    service = SafetyService(db_session)

    can_perform, reason = await service.can_perform_action(linkedin_account, "connection")

    assert can_perform is True
    assert reason == "OK"


async def test_cannot_perform_action_limit_reached(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test action denied when daily limit reached."""
    service = SafetyService(db_session)

    # Max out connections
    linkedin_account.connections_sent_today = 25
    await db_session.commit()

    can_perform, reason = await service.can_perform_action(linkedin_account, "connection")

    assert can_perform is False
    assert "Tageslimit" in reason


async def test_cannot_perform_action_suspended_account(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test action denied for suspended account."""
    service = SafetyService(db_session)

    linkedin_account.status = "suspended"
    await db_session.commit()

    can_perform, reason = await service.can_perform_action(linkedin_account, "connection")

    assert can_perform is False
    assert "gesperrt" in reason


async def test_warmup_limits_are_lower(
    db_session: AsyncSession, tenant_id: str, warmup_account: LinkedInAccount
):
    """Test that warmup accounts have lower limits."""
    service = SafetyService(db_session)

    limits = service._get_effective_limits(warmup_account)

    # Day 3 should have lower limits than full
    assert limits["connections"] < warmup_account.daily_connection_limit
    assert limits["messages"] < warmup_account.daily_message_limit
    assert limits["profiles"] < warmup_account.daily_profile_limit


async def test_full_limits_after_warmup(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test full limits for accounts past warmup."""
    service = SafetyService(db_session)

    limits = service._get_effective_limits(linkedin_account)

    assert limits["connections"] == linkedin_account.daily_connection_limit
    assert limits["messages"] == linkedin_account.daily_message_limit
    assert limits["profiles"] == linkedin_account.daily_profile_limit


async def test_record_action(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test recording an action increments counters."""
    service = SafetyService(db_session)

    initial_count = linkedin_account.connections_sent_today
    await service.record_action(linkedin_account, "connection")

    assert linkedin_account.connections_sent_today == initial_count + 1


async def test_reset_daily_counters(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test resetting daily counters."""
    service = SafetyService(db_session)

    # Set some counts
    linkedin_account.connections_sent_today = 10
    linkedin_account.messages_sent_today = 20
    await db_session.commit()

    await service.reset_daily_counters(tenant_id)
    await db_session.refresh(linkedin_account)

    assert linkedin_account.connections_sent_today == 0
    assert linkedin_account.messages_sent_today == 0


async def test_progress_warmup(
    db_session: AsyncSession, tenant_id: str, warmup_account: LinkedInAccount
):
    """Test progressing warmup day."""
    service = SafetyService(db_session)

    initial_day = warmup_account.warmup_day
    await service.progress_warmup(tenant_id)
    await db_session.refresh(warmup_account)

    assert warmup_account.warmup_day == initial_day + 1


async def test_start_warmup(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test starting warmup for an account."""
    service = SafetyService(db_session)

    await service.start_warmup(linkedin_account)
    await db_session.refresh(linkedin_account)

    assert linkedin_account.warmup_enabled is True
    assert linkedin_account.warmup_day == 0
    assert linkedin_account.warmup_started_at is not None
    assert linkedin_account.status == "warmup"


async def test_skip_warmup(
    db_session: AsyncSession, tenant_id: str, warmup_account: LinkedInAccount
):
    """Test skipping warmup."""
    service = SafetyService(db_session)

    await service.skip_warmup(warmup_account)
    await db_session.refresh(warmup_account)

    assert warmup_account.warmup_enabled is False
    assert warmup_account.warmup_day == 14
    assert warmup_account.status == "active"


async def test_calculate_optimal_delay(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test calculating optimal delay based on usage."""
    service = SafetyService(db_session)

    # Low usage - base delays
    min_delay, max_delay = await service.calculate_optimal_delay(
        linkedin_account, "connection"
    )
    assert min_delay == 30
    assert max_delay == 120

    # High usage - increased delays
    linkedin_account.connections_sent_today = 20  # 80% of limit
    await db_session.commit()

    min_delay, max_delay = await service.calculate_optimal_delay(
        linkedin_account, "connection"
    )
    assert min_delay > 30
    assert max_delay > 120


async def test_get_account_stats(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test getting account stats."""
    service = SafetyService(db_session)

    stats = await service.get_account_stats(linkedin_account)

    assert stats["account_id"] == linkedin_account.id
    assert stats["status"] == "active"
    assert "limits" in stats
    assert "connections" in stats["limits"]


# ============== Campaign Service Tests ==============


async def test_create_campaign(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test creating a campaign."""
    service = CampaignService(db_session)
    data = LinkedInCampaignCreate(
        name="Test Campaign",
        account_id=linkedin_account.id,
        steps=[
            LinkedInCampaignStepCreate(
                name="Step 1",
                order=1,
                step_type="connect",
            ),
            LinkedInCampaignStepCreate(
                name="Step 2",
                order=2,
                step_type="wait",
                wait_days=3,
            ),
        ],
    )

    campaign = await service.create(tenant_id, data)

    assert campaign.id is not None
    assert campaign.name == "Test Campaign"
    assert campaign.status == "draft"

    # Reload campaign with steps using get_by_id (uses selectinload)
    loaded_campaign = await service.get_by_id(tenant_id, campaign.id)
    assert len(loaded_campaign.steps) == 2


async def test_start_campaign(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test starting a campaign."""
    service = CampaignService(db_session)

    # Create campaign
    data = LinkedInCampaignCreate(
        name="Start Test",
        account_id=linkedin_account.id,
        steps=[
            LinkedInCampaignStepCreate(name="Step 1", order=1, step_type="connect"),
        ],
    )
    campaign = await service.create(tenant_id, data)

    # Start it
    started = await service.start(tenant_id, campaign.id)

    assert started.status == "active"
    assert started.started_at is not None


async def test_pause_campaign(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test pausing a campaign."""
    service = CampaignService(db_session)

    # Create and start campaign
    data = LinkedInCampaignCreate(
        name="Pause Test",
        account_id=linkedin_account.id,
        steps=[
            LinkedInCampaignStepCreate(name="Step 1", order=1, step_type="connect"),
        ],
    )
    campaign = await service.create(tenant_id, data)
    await service.start(tenant_id, campaign.id)

    # Pause it
    paused = await service.pause(tenant_id, campaign.id)

    assert paused.status == "paused"


async def test_add_lead_to_campaign(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test adding a lead to a campaign."""
    service = CampaignService(db_session)

    # Create campaign
    data = LinkedInCampaignCreate(
        name="Lead Test",
        account_id=linkedin_account.id,
        steps=[
            LinkedInCampaignStepCreate(name="Step 1", order=1, step_type="connect"),
        ],
    )
    campaign = await service.create(tenant_id, data)

    # Add lead
    lead_data = LinkedInCampaignLeadCreate(
        linkedin_url="https://linkedin.com/in/testuser",
        profile_name="Test User",
    )
    lead = await service.add_lead(tenant_id, campaign.id, lead_data)

    assert lead.id is not None
    assert lead.campaign_id == campaign.id
    assert lead.status == "pending"


async def test_stop_lead(
    db_session: AsyncSession, tenant_id: str, linkedin_account: LinkedInAccount
):
    """Test stopping a lead in campaign."""
    service = CampaignService(db_session)

    # Create campaign with lead
    data = LinkedInCampaignCreate(
        name="Stop Lead Test",
        account_id=linkedin_account.id,
        steps=[
            LinkedInCampaignStepCreate(name="Step 1", order=1, step_type="connect"),
        ],
    )
    campaign = await service.create(tenant_id, data)

    lead_data = LinkedInCampaignLeadCreate(
        linkedin_url="https://linkedin.com/in/testuser",
        profile_name="Test User",
    )
    lead = await service.add_lead(tenant_id, campaign.id, lead_data)

    # Stop lead
    stopped = await service.stop_lead(tenant_id, campaign.id, lead.id)

    assert stopped.status == "stopped"


# ============== Integration Tests ==============


async def test_full_campaign_workflow(
    db_session: AsyncSession,
    tenant_id: str,
    linkedin_account: LinkedInAccount,
    message_template: LinkedInMessageTemplate,
):
    """Test complete campaign workflow from creation to lead processing."""
    campaign_service = CampaignService(db_session)
    safety_service = SafetyService(db_session)

    # 1. Create campaign
    campaign_data = LinkedInCampaignCreate(
        name="Full Workflow Test",
        account_id=linkedin_account.id,
        stop_on_reply=True,
        steps=[
            LinkedInCampaignStepCreate(
                name="Connect",
                order=1,
                step_type="connect",
            ),
            LinkedInCampaignStepCreate(
                name="Wait",
                order=2,
                step_type="wait",
                wait_days=1,
            ),
            LinkedInCampaignStepCreate(
                name="Message",
                order=3,
                step_type="message",
                template_id=message_template.id,
            ),
        ],
    )
    campaign = await campaign_service.create(tenant_id, campaign_data)
    assert campaign.status == "draft"

    # 2. Add leads
    leads_data = [
        LinkedInCampaignLeadCreate(
            linkedin_url=f"https://linkedin.com/in/user{i}",
            profile_name=f"User {i}",
            company_name=f"Company {i}",
        )
        for i in range(3)
    ]

    for lead_data in leads_data:
        await campaign_service.add_lead(tenant_id, campaign.id, lead_data)

    # 3. Start campaign
    started = await campaign_service.start(tenant_id, campaign.id)
    assert started.status == "active"
    assert started.total_leads == 3

    # 4. Verify account can perform actions
    can_connect, _ = await safety_service.can_perform_action(linkedin_account, "connection")
    assert can_connect is True

    # 5. Pause campaign
    paused = await campaign_service.pause(tenant_id, campaign.id)
    assert paused.status == "paused"

    # 6. Resume campaign
    resumed = await campaign_service.start(tenant_id, campaign.id)
    assert resumed.status == "active"
