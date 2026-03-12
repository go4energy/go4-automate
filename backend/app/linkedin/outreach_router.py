"""LinkedIn outreach API router - Templates, Connections, Messages, Campaigns."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

# Activity logging imports
from app.engagement import (
    LinkedInActivityType,
    log_linkedin_activity,
)
from app.exceptions import AppError
from app.linkedin.campaign_service import CampaignService
from app.linkedin.outreach_service import (
    ConnectionService,
    MessageService,
    TemplateService,
)
from app.linkedin.schemas import (
    LinkedInActionResponse,
    LinkedInCampaignCreate,
    LinkedInCampaignLeadBulkCreate,
    LinkedInCampaignLeadBulkResult,
    LinkedInCampaignLeadCreate,
    LinkedInCampaignLeadListResponse,
    LinkedInCampaignLeadResponse,
    LinkedInCampaignListResponse,
    LinkedInCampaignResponse,
    LinkedInCampaignStepCreate,
    LinkedInCampaignStepResponse,
    LinkedInCampaignUpdate,
    LinkedInConnectionBulkCreate,
    LinkedInConnectionBulkResult,
    LinkedInConnectionCreate,
    LinkedInConnectionListResponse,
    LinkedInConnectionResponse,
    LinkedInInboxResponse,
    LinkedInMessageCreate,
    LinkedInMessageListResponse,
    LinkedInMessageResponse,
    LinkedInSendConnectionRequest,
    LinkedInSendMessageRequest,
    LinkedInTemplateCreate,
    LinkedInTemplateListResponse,
    LinkedInTemplatePreview,
    LinkedInTemplatePreviewResponse,
    LinkedInTemplateResponse,
    LinkedInTemplateUpdate,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/linkedin", tags=["linkedin-outreach"])


# ============== Template Endpoints ==============


@router.get("/templates", response_model=list[LinkedInTemplateListResponse])
async def list_templates(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(None),
    active_only: bool = Query(True),
) -> list[LinkedInTemplateListResponse]:
    """List all message templates."""
    try:
        service = TemplateService(db)
        templates = await service.list_templates(tenant_id, category, active_only)
        return [
            LinkedInTemplateListResponse(
                id=t.id,
                name=t.name,
                category=t.category,
                times_used=t.times_used,
                responses_received=t.responses_received,
                response_rate=t.responses_received / t.times_used if t.times_used > 0 else 0,
                is_active=t.is_active,
                variant_of_id=t.variant_of_id,
                created_at=t.created_at,
            )
            for t in templates
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_templates")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/templates",
    response_model=LinkedInTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: LinkedInTemplateCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInTemplateResponse:
    """Create a new message template."""
    try:
        service = TemplateService(db)
        template = await service.create(tenant_id, data)
        return _template_to_response(template)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/templates/{template_id}", response_model=LinkedInTemplateResponse)
async def get_template(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInTemplateResponse:
    """Get a template by ID."""
    try:
        service = TemplateService(db)
        template = await service.get_by_id(tenant_id, template_id)
        return _template_to_response(template)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/templates/{template_id}", response_model=LinkedInTemplateResponse)
async def update_template(
    template_id: int,
    data: LinkedInTemplateUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInTemplateResponse:
    """Update a template."""
    try:
        service = TemplateService(db)
        template = await service.update(tenant_id, template_id, data)
        return _template_to_response(template)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete (deactivate) a template."""
    try:
        service = TemplateService(db)
        await service.delete(tenant_id, template_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/templates/preview", response_model=LinkedInTemplatePreviewResponse)
async def preview_template(
    data: LinkedInTemplatePreview,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInTemplatePreviewResponse:
    """Preview a rendered template with sample data."""
    try:
        service = TemplateService(db)
        content, subject = await service.render(tenant_id, data.template_id, data.context)
        return LinkedInTemplatePreviewResponse(
            rendered_content=content,
            rendered_subject=subject,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in preview_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Connection Endpoints ==============


@router.get("/connections", response_model=list[LinkedInConnectionListResponse])
async def list_connections(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    campaign_id: int | None = Query(None),
) -> list[LinkedInConnectionListResponse]:
    """List all connection requests."""
    try:
        service = ConnectionService(db)
        connections = await service.list_connections(
            tenant_id, account_id, status_filter, campaign_id
        )
        return [
            LinkedInConnectionListResponse(
                id=c.id,
                account_id=c.account_id,
                linkedin_url=c.linkedin_url,
                profile_name=c.profile_name,
                profile_headline=c.profile_headline,
                status=c.status,
                sent_at=c.sent_at,
                accepted_at=c.accepted_at,
                campaign_id=c.campaign_id,
                created_at=c.created_at,
            )
            for c in connections
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_connections")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/connections",
    response_model=LinkedInConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connection(
    data: LinkedInConnectionCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInConnectionResponse:
    """Create a connection request (queued for sending)."""
    try:
        service = ConnectionService(db)
        connection = await service.create(tenant_id, data)
        return LinkedInConnectionResponse.model_validate(connection)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_connection")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/connections/bulk", response_model=LinkedInConnectionBulkResult)
async def create_connections_bulk(
    data: LinkedInConnectionBulkCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInConnectionBulkResult:
    """Create connection requests for multiple contacts."""
    try:
        service = ConnectionService(db)
        return await service.create_bulk(tenant_id, data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_connections_bulk")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/connections/{connection_id}", response_model=LinkedInConnectionResponse)
async def get_connection(
    connection_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInConnectionResponse:
    """Get a connection by ID."""
    try:
        service = ConnectionService(db)
        connection = await service.get_by_id(tenant_id, connection_id)
        return LinkedInConnectionResponse.model_validate(connection)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_connection")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/connections/{connection_id}/withdraw", response_model=LinkedInConnectionResponse)
async def withdraw_connection(
    connection_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInConnectionResponse:
    """Withdraw a pending connection request."""
    try:
        service = ConnectionService(db)
        connection = await service.withdraw(tenant_id, connection_id)
        return LinkedInConnectionResponse.model_validate(connection)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in withdraw_connection")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Message Endpoints ==============


@router.get("/messages", response_model=list[LinkedInMessageListResponse])
async def list_messages(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
    direction: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    campaign_id: int | None = Query(None),
) -> list[LinkedInMessageListResponse]:
    """List all messages."""
    try:
        service = MessageService(db)
        messages = await service.list_messages(
            tenant_id, account_id, direction, status_filter, campaign_id
        )
        return [
            LinkedInMessageListResponse(
                id=m.id,
                account_id=m.account_id,
                linkedin_url=m.linkedin_url,
                profile_name=m.profile_name,
                message_type=m.message_type,
                direction=m.direction,
                content_preview=m.content[:100] if m.content else "",
                status=m.status,
                sent_at=m.sent_at,
                replied_at=m.replied_at,
                campaign_id=m.campaign_id,
                created_at=m.created_at,
            )
            for m in messages
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_messages")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/messages",
    response_model=LinkedInMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    data: LinkedInMessageCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInMessageResponse:
    """Create a message (queued for sending)."""
    try:
        service = MessageService(db)
        message = await service.create(tenant_id, data)
        return LinkedInMessageResponse.model_validate(message)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_message")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/messages/{message_id}", response_model=LinkedInMessageResponse)
async def get_message(
    message_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInMessageResponse:
    """Get a message by ID."""
    try:
        service = MessageService(db)
        message = await service.get_by_id(tenant_id, message_id)
        return LinkedInMessageResponse.model_validate(message)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_message")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/inbox", response_model=list[LinkedInInboxResponse])
async def get_inbox(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
) -> list[LinkedInInboxResponse]:
    """Get inbox conversations."""
    try:
        service = MessageService(db)
        conversations = await service.get_inbox(tenant_id, account_id)
        return [LinkedInInboxResponse(**conv) for conv in conversations]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_inbox")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Campaign Endpoints ==============


@router.get("/campaigns", response_model=list[LinkedInCampaignListResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    pipeline_id: int | None = Query(None),
) -> list[LinkedInCampaignListResponse]:
    """List all campaigns."""
    try:
        service = CampaignService(db)
        campaigns = await service.list_campaigns(
            tenant_id, account_id, status_filter, pipeline_id
        )
        return [_campaign_to_list_response(c) for c in campaigns]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns",
    response_model=LinkedInCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: LinkedInCampaignCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignResponse:
    """Create a new campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.create(tenant_id, data)
        campaign = await service.get_by_id(tenant_id, campaign.id)
        return _campaign_to_response(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/campaigns/{campaign_id}", response_model=LinkedInCampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignResponse:
    """Get a campaign by ID."""
    try:
        service = CampaignService(db)
        campaign = await service.get_by_id(tenant_id, campaign_id)
        return _campaign_to_response(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/campaigns/{campaign_id}", response_model=LinkedInCampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: LinkedInCampaignUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignResponse:
    """Update a campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.update(tenant_id, campaign_id, data)
        campaign = await service.get_by_id(tenant_id, campaign.id)
        return _campaign_to_response(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a campaign."""
    try:
        service = CampaignService(db)
        await service.delete(tenant_id, campaign_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns/{campaign_id}/start", response_model=LinkedInCampaignResponse)
async def start_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignResponse:
    """Start a campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.start(tenant_id, campaign_id)
        campaign = await service.get_by_id(tenant_id, campaign.id)
        return _campaign_to_response(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in start_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns/{campaign_id}/pause", response_model=LinkedInCampaignResponse)
async def pause_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignResponse:
    """Pause a campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.pause(tenant_id, campaign_id)
        campaign = await service.get_by_id(tenant_id, campaign.id)
        return _campaign_to_response(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in pause_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Campaign Steps ==============


@router.post(
    "/campaigns/{campaign_id}/steps",
    response_model=LinkedInCampaignStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_campaign_step(
    campaign_id: int,
    data: LinkedInCampaignStepCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignStepResponse:
    """Add a step to a campaign."""
    try:
        service = CampaignService(db)
        step = await service.add_step(tenant_id, campaign_id, data)
        return _step_to_response(step)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in add_campaign_step")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/campaigns/{campaign_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_campaign_step(
    campaign_id: int,
    step_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a campaign step."""
    try:
        service = CampaignService(db)
        await service.delete_step(tenant_id, campaign_id, step_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_campaign_step")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Campaign Leads ==============


@router.get("/campaigns/{campaign_id}/leads", response_model=list[LinkedInCampaignLeadListResponse])
async def list_campaign_leads(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[LinkedInCampaignLeadListResponse]:
    """List leads in a campaign."""
    try:
        service = CampaignService(db)
        leads = await service.list_leads(tenant_id, campaign_id, status_filter)
        return [
            LinkedInCampaignLeadListResponse(
                id=lead.id,
                linkedin_url=lead.linkedin_url,
                profile_name=lead.profile_name,
                company_name=lead.company_name,
                status=lead.status,
                connection_status=lead.connection_status,
                has_replied=lead.has_replied,
                current_step_order=lead.current_step_order,
                current_step_name=lead.current_step.name if lead.current_step else None,
                next_action_at=lead.next_action_at,
                created_at=lead.created_at,
            )
            for lead in leads
        ]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_campaign_leads")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns/{campaign_id}/leads",
    response_model=LinkedInCampaignLeadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_campaign_lead(
    campaign_id: int,
    data: LinkedInCampaignLeadCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignLeadResponse:
    """Add a lead to a campaign."""
    try:
        service = CampaignService(db)
        lead = await service.add_lead(tenant_id, campaign_id, data)
        return _lead_to_response(lead)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in add_campaign_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns/{campaign_id}/leads/bulk",
    response_model=LinkedInCampaignLeadBulkResult,
)
async def add_campaign_leads_bulk(
    campaign_id: int,
    data: LinkedInCampaignLeadBulkCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignLeadBulkResult:
    """Add multiple leads from contacts."""
    try:
        service = CampaignService(db)
        return await service.add_leads_bulk(tenant_id, campaign_id, data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in add_campaign_leads_bulk")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/campaigns/{campaign_id}/leads/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_campaign_lead(
    campaign_id: int,
    lead_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a lead from campaign."""
    try:
        service = CampaignService(db)
        await service.remove_lead(tenant_id, campaign_id, lead_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in remove_campaign_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns/{campaign_id}/leads/{lead_id}/stop",
    response_model=LinkedInCampaignLeadResponse,
)
async def stop_campaign_lead(
    campaign_id: int,
    lead_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInCampaignLeadResponse:
    """Stop a lead in campaign."""
    try:
        service = CampaignService(db)
        lead = await service.stop_lead(tenant_id, campaign_id, lead_id)
        return _lead_to_response(lead)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in stop_campaign_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Helper: Find Contact by LinkedIn URL ==============


async def _find_contact_by_linkedin_url(
    db: AsyncSession, tenant_id: str, linkedin_url: str
) -> int | None:
    """Find contact_id by LinkedIn URL.

    Tries to match the URL against the contacts.linkedin field.
    Returns None if no matching contact is found.
    """
    from sqlalchemy import select

    from app.contacts.models import Contact

    # Normalize URL for comparison (remove trailing slashes, etc.)
    normalized_url = linkedin_url.rstrip("/")

    # Try exact match first
    result = await db.execute(
        select(Contact.id).where(
            Contact.tenant_id == tenant_id,
            Contact.linkedin == normalized_url,
        )
    )
    contact_id = result.scalar_one_or_none()
    if contact_id:
        return contact_id

    # Try matching with/without trailing slash
    result = await db.execute(
        select(Contact.id).where(
            Contact.tenant_id == tenant_id,
            Contact.linkedin == f"{normalized_url}/",
        )
    )
    contact_id = result.scalar_one_or_none()
    if contact_id:
        return contact_id

    # Try to extract and match just the username part
    # e.g., "https://www.linkedin.com/in/username" -> "username"
    import re

    match = re.search(r"linkedin\.com/in/([^/?]+)", linkedin_url)
    if match:
        username = match.group(1)
        # Search for any URL containing this username
        result = await db.execute(
            select(Contact.id).where(
                Contact.tenant_id == tenant_id,
                Contact.linkedin.ilike(f"%/in/{username}%"),
            )
        )
        contact_id = result.scalar_one_or_none()
        if contact_id:
            return contact_id

    return None


# ============== Immediate Action Endpoints ==============


@router.post("/actions/send-connection", response_model=LinkedInActionResponse)
async def send_connection_immediately(
    data: LinkedInSendConnectionRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInActionResponse:
    """Send a connection request immediately (uses browser)."""
    from sqlalchemy import select

    from app.linkedin.models import LinkedInAccount
    from app.linkedin.scraper.browser import LinkedInBrowser

    try:
        # Get account
        account_result = await db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == data.account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account nicht gefunden")
        if account.status != "active":
            raise HTTPException(status_code=400, detail="Account nicht aktiv")

        # Check limits
        limits = account.get_effective_limits()
        if account.connections_sent_today >= limits["connections"]:
            raise HTTPException(
                status_code=429,
                detail=f"Tageslimit erreicht ({limits['connections']} Verbindungen)",
            )

        # Create connection record
        conn_service = ConnectionService(db)
        from app.linkedin.schemas import LinkedInConnectionCreate
        connection = await conn_service.create(
            tenant_id,
            LinkedInConnectionCreate(
                account_id=data.account_id,
                linkedin_url=data.linkedin_url,
                profile_name="Unknown",  # Will be updated
                message=data.message,
                template_id=data.template_id,
            ),
        )

        # Send via browser
        browser = LinkedInBrowser(headless=False)
        try:
            await browser.start(account.email, account.session_data)
            result = await browser.send_connection_request(data.linkedin_url, data.message)

            if result["success"]:
                await conn_service.mark_sent(connection.id)
                account.connections_sent_today += 1

                # Log activity if contact is found
                contact_id = await _find_contact_by_linkedin_url(
                    db, tenant_id, data.linkedin_url
                )
                if contact_id:
                    try:
                        await log_linkedin_activity(
                            db=db,
                            tenant_id=tenant_id,
                            contact_id=contact_id,
                            activity_type=LinkedInActivityType.CONNECTION_REQUEST_SENT,
                            content=data.message,
                            external_id=str(connection.id),
                            metadata={
                                "linkedin_url": data.linkedin_url,
                                "account_id": data.account_id,
                            },
                            commit=False,
                        )
                    except Exception as e:
                        logger.warning(
                            "Activity logging failed for connection {id}: {err}",
                            id=connection.id,
                            err=str(e),
                        )

                await db.commit()

                return LinkedInActionResponse(
                    success=True,
                    message="Verbindungsanfrage gesendet",
                    connection_id=connection.id,
                )
            else:
                await conn_service.mark_error(connection.id, result.get("error", "Unbekannter Fehler"))
                await db.commit()

                return LinkedInActionResponse(
                    success=False,
                    message=result.get("error", "Fehler beim Senden"),
                    connection_id=connection.id,
                )
        finally:
            await browser.stop()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in send_connection_immediately")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/actions/send-message", response_model=LinkedInActionResponse)
async def send_message_immediately(
    data: LinkedInSendMessageRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LinkedInActionResponse:
    """Send a message immediately (uses browser)."""
    from sqlalchemy import select

    from app.linkedin.models import LinkedInAccount
    from app.linkedin.scraper.browser import LinkedInBrowser

    try:
        # Get account
        account_result = await db.execute(
            select(LinkedInAccount).where(
                LinkedInAccount.id == data.account_id,
                LinkedInAccount.tenant_id == tenant_id,
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account nicht gefunden")
        if account.status != "active":
            raise HTTPException(status_code=400, detail="Account nicht aktiv")

        # Check limits
        limits = account.get_effective_limits()
        if account.messages_sent_today >= limits["messages"]:
            raise HTTPException(
                status_code=429,
                detail=f"Tageslimit erreicht ({limits['messages']} Nachrichten)",
            )

        # Create message record
        msg_service = MessageService(db)
        from app.linkedin.schemas import LinkedInMessageCreate
        message = await msg_service.create(
            tenant_id,
            LinkedInMessageCreate(
                account_id=data.account_id,
                linkedin_url=data.linkedin_url,
                profile_name="Unknown",
                content=data.content,
                subject=data.subject,
                template_id=data.template_id,
            ),
        )

        # Send via browser
        browser = LinkedInBrowser(headless=False)
        try:
            await browser.start(account.email, account.session_data)
            result = await browser.send_message(data.linkedin_url, data.content, data.subject)

            if result["success"]:
                await msg_service.mark_sent(message.id)
                account.messages_sent_today += 1

                # Log activity if contact is found
                contact_id = await _find_contact_by_linkedin_url(
                    db, tenant_id, data.linkedin_url
                )
                if contact_id:
                    try:
                        await log_linkedin_activity(
                            db=db,
                            tenant_id=tenant_id,
                            contact_id=contact_id,
                            activity_type=LinkedInActivityType.MESSAGE_SENT,
                            subject=data.subject,
                            content=data.content,
                            external_id=str(message.id),
                            metadata={
                                "linkedin_url": data.linkedin_url,
                                "account_id": data.account_id,
                                "message_type": "direct",
                            },
                            commit=False,
                        )
                    except Exception as e:
                        logger.warning(
                            "Activity logging failed for message {id}: {err}",
                            id=message.id,
                            err=str(e),
                        )

                await db.commit()

                return LinkedInActionResponse(
                    success=True,
                    message="Nachricht gesendet",
                    message_id=message.id,
                )
            else:
                await msg_service.mark_error(message.id, result.get("error", "Unbekannter Fehler"))
                await db.commit()

                return LinkedInActionResponse(
                    success=False,
                    message=result.get("error", "Fehler beim Senden"),
                    message_id=message.id,
                )
        finally:
            await browser.stop()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in send_message_immediately")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============== Helper Functions ==============


def _template_to_response(template) -> LinkedInTemplateResponse:
    return LinkedInTemplateResponse(
        id=template.id,
        tenant_id=template.tenant_id,
        name=template.name,
        category=template.category,
        subject=template.subject,
        content=template.content,
        variables=template.variables,
        variant_of_id=template.variant_of_id,
        variant_name=template.variant_name,
        times_used=template.times_used,
        responses_received=template.responses_received,
        response_rate=template.responses_received / template.times_used if template.times_used > 0 else 0,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _campaign_to_response(campaign) -> LinkedInCampaignResponse:
    return LinkedInCampaignResponse(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        account_id=campaign.account_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        timezone=campaign.timezone,
        daily_connection_limit=campaign.daily_connection_limit,
        daily_message_limit=campaign.daily_message_limit,
        schedule_days=campaign.schedule_days,
        schedule_start_time=campaign.schedule_start_time,
        schedule_end_time=campaign.schedule_end_time,
        stop_on_reply=campaign.stop_on_reply,
        stop_on_connect=campaign.stop_on_connect,
        total_leads=campaign.total_leads,
        leads_completed=campaign.leads_completed,
        leads_active=campaign.leads_active,
        connections_sent=campaign.connections_sent,
        connections_accepted=campaign.connections_accepted,
        messages_sent=campaign.messages_sent,
        replies_received=campaign.replies_received,
        connection_rate=campaign.connections_accepted / campaign.connections_sent if campaign.connections_sent > 0 else 0,
        reply_rate=campaign.replies_received / campaign.messages_sent if campaign.messages_sent > 0 else 0,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        account_name=campaign.account.name if campaign.account else None,
        steps=[_step_to_response(s) for s in campaign.steps],
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _campaign_to_list_response(campaign) -> LinkedInCampaignListResponse:
    return LinkedInCampaignListResponse(
        id=campaign.id,
        account_id=campaign.account_id,
        name=campaign.name,
        status=campaign.status,
        total_leads=campaign.total_leads,
        leads_active=campaign.leads_active,
        leads_completed=campaign.leads_completed,
        connections_sent=campaign.connections_sent,
        connections_accepted=campaign.connections_accepted,
        messages_sent=campaign.messages_sent,
        replies_received=campaign.replies_received,
        connection_rate=campaign.connections_accepted / campaign.connections_sent if campaign.connections_sent > 0 else 0,
        reply_rate=campaign.replies_received / campaign.messages_sent if campaign.messages_sent > 0 else 0,
        account_name=campaign.account.name if campaign.account else None,
        started_at=campaign.started_at,
        created_at=campaign.created_at,
    )


def _step_to_response(step) -> LinkedInCampaignStepResponse:
    return LinkedInCampaignStepResponse(
        id=step.id,
        campaign_id=step.campaign_id,
        name=step.name,
        order=step.order,
        step_type=step.step_type,
        wait_days=step.wait_days,
        wait_hours=step.wait_hours,
        template_id=step.template_id,
        template_ids=step.template_ids,
        ab_test_enabled=step.ab_test_enabled,
        condition_type=step.condition_type,
        condition_true_step_id=step.condition_true_step_id,
        condition_false_step_id=step.condition_false_step_id,
        leads_entered=step.leads_entered,
        leads_completed=step.leads_completed,
        leads_failed=step.leads_failed,
        is_active=step.is_active,
        template_name=step.template.name if step.template else None,
        created_at=step.created_at,
    )


def _lead_to_response(lead) -> LinkedInCampaignLeadResponse:
    return LinkedInCampaignLeadResponse(
        id=lead.id,
        campaign_id=lead.campaign_id,
        contact_id=lead.contact_id,
        linkedin_url=lead.linkedin_url,
        linkedin_id=lead.linkedin_id,
        profile_name=lead.profile_name,
        profile_headline=lead.profile_headline,
        company_name=lead.company_name,
        profile_picture_url=lead.profile_picture_url,
        custom_variables=lead.custom_variables,
        current_step_id=lead.current_step_id,
        current_step_order=lead.current_step_order,
        status=lead.status,
        connection_status=lead.connection_status,
        has_replied=lead.has_replied,
        reply_received_at=lead.reply_received_at,
        entered_campaign_at=lead.entered_campaign_at,
        next_action_at=lead.next_action_at,
        completed_at=lead.completed_at,
        error_message=lead.error_message,
        ab_variant=lead.ab_variant,
        current_step_name=lead.current_step.name if lead.current_step else None,
        created_at=lead.created_at,
    )


# ============== Safety & Warmup Endpoints ==============


@router.get("/accounts/{account_id}/safety")
async def get_account_safety_stats(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get safety stats and limits for an account."""
    from app.linkedin.safety_service import SafetyService

    try:
        service = SafetyService(db)
        account = await service.get_account(account_id, tenant_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account nicht gefunden")

        return await service.get_account_stats(account)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in get_account_safety_stats")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/accounts/{account_id}/warmup/start")
async def start_account_warmup(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Start warmup period for an account."""
    from app.linkedin.safety_service import SafetyService

    try:
        service = SafetyService(db)
        account = await service.get_account(account_id, tenant_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account nicht gefunden")

        await service.start_warmup(account)
        return {"success": True, "message": "Warmup gestartet"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in start_account_warmup")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/accounts/{account_id}/warmup/skip")
async def skip_account_warmup(
    account_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Skip warmup for an experienced account."""
    from app.linkedin.safety_service import SafetyService

    try:
        service = SafetyService(db)
        account = await service.get_account(account_id, tenant_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account nicht gefunden")

        await service.skip_warmup(account)
        return {"success": True, "message": "Warmup uebersprungen"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in skip_account_warmup")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/safety/tenant-stats")
async def get_tenant_safety_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get safety stats for all accounts in tenant."""
    from app.linkedin.safety_service import SafetyService

    try:
        service = SafetyService(db)
        return await service.get_tenant_stats(tenant_id)
    except Exception as e:
        logger.exception("Fehler in get_tenant_safety_stats")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============== Campaign Processing Endpoints ==============


@router.post("/campaigns/{campaign_id}/process")
async def process_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process a campaign - execute pending steps for all ready leads.

    This should typically be called by a background worker,
    but can also be triggered manually.
    """
    from app.linkedin.campaign_worker import CampaignWorker

    try:
        worker = CampaignWorker(db)
        result = await worker.process_campaign(campaign_id, tenant_id)
        return result
    except Exception as e:
        logger.exception("Fehler in process_campaign")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/campaigns/{campaign_id}/check-replies")
async def check_campaign_replies(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check for replies to messages in a campaign."""
    from app.linkedin.campaign_worker import CampaignWorker

    try:
        worker = CampaignWorker(db)
        result = await worker.check_for_replies(campaign_id, tenant_id)
        return result
    except Exception as e:
        logger.exception("Fehler in check_campaign_replies")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/maintenance/daily")
async def run_daily_maintenance(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run daily maintenance tasks.

    This resets daily counters and progresses warmup.
    Should be called once per day at midnight.
    """
    from app.linkedin.campaign_worker import run_daily_maintenance as daily_maintenance

    try:
        result = await daily_maintenance(db)
        return result
    except Exception as e:
        logger.exception("Fehler in run_daily_maintenance")
        raise HTTPException(status_code=500, detail=str(e)) from e
