"""Email Marketing API router - main CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.emailmarketing.config_schema import emailmarketing_interface
from app.emailmarketing.schemas import (
    CampaignScheduleRequest,
    CampaignStats,
    CampaignTestRequest,
    EmailCampaignCreate,
    EmailCampaignListResponse,
    EmailCampaignResponse,
    EmailCampaignUpdate,
    EmailProviderCreate,
    EmailProviderListResponse,
    EmailProviderResponse,
    EmailProviderUpdate,
    EmailRecipientResponse,
    EmailSequenceCreate,
    EmailSequenceListResponse,
    EmailSequenceResponse,
    EmailSequenceStepCreate,
    EmailSequenceStepResponse,
    EmailSequenceStepUpdate,
    EmailSequenceUpdate,
    EmailTemplateCreate,
    EmailTemplateListResponse,
    EmailTemplatePreview,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    EnrollContactsRequest,
    RecipientListParams,
)
from app.emailmarketing.service import (
    EmailCampaignService,
    EmailProviderService,
    EmailSequenceService,
    EmailTemplateService,
)
from app.emailmarketing.tracking import replace_merge_tags
from app.exceptions import AppError, DuplicateError, NotFoundError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/emailmarketing", tags=["emailmarketing"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
emailmarketing_interface.register_endpoints(router)


# ============== Provider Endpoints ==============


@router.get("/providers", response_model=list[EmailProviderListResponse])
async def list_providers(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[EmailProviderListResponse]:
    """List all email providers."""
    try:
        service = EmailProviderService(db)
        providers = await service.list_providers(tenant_id)
        return [EmailProviderListResponse.model_validate(p) for p in providers]
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in list_providers")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/providers",
    response_model=EmailProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider(
    data: EmailProviderCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailProviderResponse:
    """Create a new email provider."""
    try:
        service = EmailProviderService(db)
        provider = await service.create(tenant_id, data)
        return EmailProviderResponse.model_validate(provider)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_provider")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/providers/{provider_id}", response_model=EmailProviderResponse)
async def get_provider(
    provider_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailProviderResponse:
    """Get a provider by ID."""
    try:
        service = EmailProviderService(db)
        provider = await service.get_by_id(tenant_id, provider_id)
        return EmailProviderResponse.model_validate(provider)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_provider")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/providers/{provider_id}", response_model=EmailProviderResponse)
async def update_provider(
    provider_id: int,
    data: EmailProviderUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailProviderResponse:
    """Update a provider."""
    try:
        service = EmailProviderService(db)
        provider = await service.update(tenant_id, provider_id, data)
        return EmailProviderResponse.model_validate(provider)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_provider")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a provider."""
    try:
        service = EmailProviderService(db)
        await service.delete(tenant_id, provider_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_provider")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/providers/{provider_id}/verify")
async def verify_provider(
    provider_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify provider credentials."""
    try:
        service = EmailProviderService(db)
        valid = await service.verify(tenant_id, provider_id)
        return {"valid": valid}
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in verify_provider")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Template Endpoints ==============


@router.get("/templates", response_model=list[EmailTemplateListResponse])
async def list_templates(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(False),
) -> list[EmailTemplateListResponse]:
    """List all email templates."""
    try:
        service = EmailTemplateService(db)
        templates = await service.list_templates(tenant_id, active_only)
        return [EmailTemplateListResponse.model_validate(t) for t in templates]
    except Exception as e:
        logger.exception("Fehler in list_templates")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/templates",
    response_model=EmailTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: EmailTemplateCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    """Create a new email template."""
    try:
        service = EmailTemplateService(db)
        template = await service.create(tenant_id, data)
        return EmailTemplateResponse.model_validate(template)
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/templates/{template_id}", response_model=EmailTemplateResponse)
async def get_template(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    """Get a template by ID."""
    try:
        service = EmailTemplateService(db)
        template = await service.get_by_id(tenant_id, template_id)
        return EmailTemplateResponse.model_validate(template)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/templates/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    template_id: int,
    data: EmailTemplateUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailTemplateResponse:
    """Update a template."""
    try:
        service = EmailTemplateService(db)
        template = await service.update(tenant_id, template_id, data)
        return EmailTemplateResponse.model_validate(template)
    except NotFoundError as e:
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
    """Delete a template."""
    try:
        service = EmailTemplateService(db)
        await service.delete(tenant_id, template_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/templates/preview")
async def preview_template(
    data: EmailTemplatePreview,
) -> dict:
    """Preview a template with merge data."""
    try:
        html = replace_merge_tags(data.html_content, data.merge_data)
        return {"html": html}
    except Exception as e:
        logger.exception("Fehler in preview_template")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Campaign Endpoints ==============


@router.get("/campaigns", response_model=list[EmailCampaignListResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    pipeline_id: int | None = Query(None),
) -> list[EmailCampaignListResponse]:
    """List all campaigns."""
    try:
        service = EmailCampaignService(db)
        campaigns = await service.list_campaigns(tenant_id, status_filter, pipeline_id)
        return [EmailCampaignListResponse.model_validate(c) for c in campaigns]
    except Exception as e:
        logger.exception("Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/campaigns",
    response_model=EmailCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: EmailCampaignCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignResponse:
    """Create a new campaign."""
    try:
        service = EmailCampaignService(db)
        campaign = await service.create(tenant_id, data)
        return EmailCampaignResponse.model_validate(campaign)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/campaigns/{campaign_id}", response_model=EmailCampaignResponse)
async def get_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignResponse:
    """Get a campaign by ID."""
    try:
        service = EmailCampaignService(db)
        campaign = await service.get_by_id(tenant_id, campaign_id)
        return EmailCampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/campaigns/{campaign_id}", response_model=EmailCampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: EmailCampaignUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignResponse:
    """Update a campaign."""
    try:
        service = EmailCampaignService(db)
        campaign = await service.update(tenant_id, campaign_id, data)
        return EmailCampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
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
        service = EmailCampaignService(db)
        await service.delete(tenant_id, campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a campaign immediately."""
    try:
        service = EmailCampaignService(db)
        sent_count = await service.send_campaign(tenant_id, campaign_id)
        return {"sent": sent_count}
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in send_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns/{campaign_id}/schedule", response_model=EmailCampaignResponse)
async def schedule_campaign(
    campaign_id: int,
    data: CampaignScheduleRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailCampaignResponse:
    """Schedule a campaign for later."""
    try:
        service = EmailCampaignService(db)
        campaign = await service.schedule_campaign(
            tenant_id, campaign_id, data.scheduled_at
        )
        return EmailCampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in schedule_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns/{campaign_id}/test")
async def test_campaign(
    campaign_id: int,
    data: CampaignTestRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a test email."""
    try:
        service = EmailCampaignService(db)
        success = await service.send_test(
            tenant_id, campaign_id, data.to, data.merge_data
        )
        return {"success": success}
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in test_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignStats:
    """Get campaign statistics."""
    try:
        service = EmailCampaignService(db)
        return await service.get_stats(tenant_id, campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_campaign_stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/campaigns/{campaign_id}/recipients", response_model=list[EmailRecipientResponse])
async def get_campaign_recipients(
    campaign_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[EmailRecipientResponse]:
    """Get campaign recipients."""
    try:
        service = EmailCampaignService(db)
        params = RecipientListParams(
            status=status_filter, search=search, limit=limit, offset=offset
        )
        recipients, _ = await service.get_recipients(tenant_id, campaign_id, params)
        return [EmailRecipientResponse.model_validate(r) for r in recipients]
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_campaign_recipients")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Sequence Endpoints ==============


@router.get("/sequences", response_model=list[EmailSequenceListResponse])
async def list_sequences(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    pipeline_id: int | None = Query(None),
) -> list[EmailSequenceListResponse]:
    """List all sequences."""
    try:
        service = EmailSequenceService(db)
        sequences = await service.list_sequences(tenant_id, status_filter, pipeline_id)
        return [EmailSequenceListResponse(**s) for s in sequences]
    except Exception as e:
        logger.exception("Fehler in list_sequences")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/sequences",
    response_model=EmailSequenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sequence(
    data: EmailSequenceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceResponse:
    """Create a new sequence."""
    try:
        service = EmailSequenceService(db)
        sequence = await service.create(tenant_id, data)
        return EmailSequenceResponse.model_validate(sequence)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in create_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sequences/{sequence_id}", response_model=EmailSequenceResponse)
async def get_sequence(
    sequence_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceResponse:
    """Get a sequence by ID."""
    try:
        service = EmailSequenceService(db)
        sequence = await service.get_by_id(tenant_id, sequence_id)
        return EmailSequenceResponse.model_validate(sequence)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/sequences/{sequence_id}", response_model=EmailSequenceResponse)
async def update_sequence(
    sequence_id: int,
    data: EmailSequenceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceResponse:
    """Update a sequence."""
    try:
        service = EmailSequenceService(db)
        sequence = await service.update(tenant_id, sequence_id, data)
        return EmailSequenceResponse.model_validate(sequence)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/sequences/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a sequence."""
    try:
        service = EmailSequenceService(db)
        await service.delete(tenant_id, sequence_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/sequences/{sequence_id}/activate", response_model=EmailSequenceResponse)
async def activate_sequence(
    sequence_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceResponse:
    """Activate a sequence."""
    try:
        service = EmailSequenceService(db)
        sequence = await service.activate(tenant_id, sequence_id)
        return EmailSequenceResponse.model_validate(sequence)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in activate_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/sequences/{sequence_id}/pause", response_model=EmailSequenceResponse)
async def pause_sequence(
    sequence_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceResponse:
    """Pause a sequence."""
    try:
        service = EmailSequenceService(db)
        sequence = await service.pause(tenant_id, sequence_id)
        return EmailSequenceResponse.model_validate(sequence)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in pause_sequence")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Sequence Steps ==============


@router.post(
    "/sequences/{sequence_id}/steps",
    response_model=EmailSequenceStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_sequence_step(
    sequence_id: int,
    data: EmailSequenceStepCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceStepResponse:
    """Add a step to a sequence."""
    try:
        service = EmailSequenceService(db)
        step = await service.add_step(tenant_id, sequence_id, data)
        return EmailSequenceStepResponse.model_validate(step)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in add_sequence_step")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put(
    "/sequences/{sequence_id}/steps/{step_id}",
    response_model=EmailSequenceStepResponse,
)
async def update_sequence_step(
    sequence_id: int,
    step_id: int,
    data: EmailSequenceStepUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailSequenceStepResponse:
    """Update a sequence step."""
    try:
        service = EmailSequenceService(db)
        step = await service.update_step(tenant_id, sequence_id, step_id, data)
        return EmailSequenceStepResponse.model_validate(step)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_sequence_step")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/sequences/{sequence_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sequence_step(
    sequence_id: int,
    step_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a sequence step."""
    try:
        service = EmailSequenceService(db)
        await service.delete_step(tenant_id, sequence_id, step_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_sequence_step")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Sequence Enrollments ==============


@router.post("/sequences/{sequence_id}/enroll")
async def enroll_contacts(
    sequence_id: int,
    data: EnrollContactsRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enroll contacts in a sequence."""
    try:
        service = EmailSequenceService(db)
        enrolled = await service.enroll_contacts(tenant_id, sequence_id, data.contact_ids)
        return {"enrolled": enrolled}
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in enroll_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sequences/{sequence_id}/enrollments")
async def get_sequence_enrollments(
    sequence_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[dict]:
    """Get sequence enrollments."""
    try:
        service = EmailSequenceService(db)
        enrollments = await service.get_enrollments(tenant_id, sequence_id, status_filter)
        return [
            {
                "id": e.id,
                "contact_id": e.contact_id,
                "contact_name": e.contact.name if e.contact else None,
                "contact_email": e.contact.email if e.contact else None,
                "current_step": e.current_step,
                "status": e.status,
                "next_send_at": e.next_send_at,
                "enrolled_at": e.enrolled_at,
                "completed_at": e.completed_at,
            }
            for e in enrollments
        ]
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in get_sequence_enrollments")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Engagement Actions Queue ==============


@router.get("/engagement/actions")
async def get_engagement_actions(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get pending engagement actions for Email.

    These are actions created by the Engagement Brain that need to be
    processed by the Email module.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction

    try:
        query = (
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
            )
            .where(
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "email",
            )
        )

        if status_filter:
            query = query.where(PendingAction.status == status_filter)
        else:
            query = query.where(
                PendingAction.status.in_(["pending", "ready_for_approval", "approved"])
            )

        query = query.order_by(
            PendingAction.priority.desc(),
            PendingAction.due_at.asc().nullslast(),
            PendingAction.created_at.asc(),
        ).limit(limit)

        result = await db.execute(query)
        actions = result.scalars().all()

        return [
            {
                "id": a.id,
                "contact_id": a.contact_id,
                "contact_name": a.contact.name if a.contact else None,
                "contact_email": a.contact.email if a.contact else None,
                "pipeline_id": a.pipeline_id,
                "pipeline_name": a.pipeline.name if a.pipeline else None,
                "action_type": a.action_type,
                "context": a.context,
                "suggested_content": a.suggested_content,
                "priority": a.priority,
                "due_at": a.due_at,
                "needs_approval": a.needs_approval,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in actions
        ]
    except Exception as e:
        logger.exception("Error getting engagement actions")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/engagement/actions/{action_id}/generate-content")
async def generate_action_content(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate email content for a pending action.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction
    from app.services.llm import LLMService

    try:
        result = await db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "email",
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Aktion nicht gefunden")

        context = action.context or {}
        pipeline = action.pipeline
        contact = action.contact

        prompt = f"""
Schreibe eine professionelle E-Mail.

EMPFÄNGER:
- Name: {context.get('contact_name', contact.name if contact else 'Kunde')}
- E-Mail: {context.get('contact_email', contact.email if contact else '')}
- Position: {context.get('contact_position', '')}
- Unternehmen: {context.get('contact_company', '')}

KONTEXT:
- Produkt: {context.get('product_name', pipeline.product_name if pipeline else '')}
- Ziel: {context.get('goal', pipeline.goal if pipeline else '')}
- Tonalität: {context.get('tone_of_voice', pipeline.tone_of_voice if pipeline else 'professionell')}
- Bisherige Kontakte: {context.get('touch_count', 0)}

Antworte im JSON-Format:
{{
    "subject": "Betreffzeile (max 60 Zeichen)",
    "body": "E-Mail-Inhalt"
}}
"""

        llm = LLMService()
        content = await llm.generate_json(task="content", prompt=prompt)

        # Update action with generated content
        action.suggested_content = f"Betreff: {content.get('subject', '')}\n\n{content.get('body', '')}"
        await db.commit()

        return {
            "action_id": action_id,
            "generated_subject": content.get("subject", ""),
            "generated_body": content.get("body", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating action content")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/engagement/actions/{action_id}/execute")
async def execute_engagement_action(
    action_id: int,
    subject_override: str | None = None,
    body_override: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Execute an email engagement action.

    This will send the email and mark the action as completed.
    """
    from datetime import datetime

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.emailmarketing.service import EmailCampaignService
    from app.engagement.models import PendingAction

    try:
        result = await db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
                selectinload(PendingAction.enrollment),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "email",
                PendingAction.status.in_(["approved", "pending"]),
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(
                status_code=404,
                detail="Aktion nicht gefunden oder nicht ausführbar",
            )

        contact = action.contact
        if not contact or not contact.email:
            raise HTTPException(
                status_code=400,
                detail="Kontakt hat keine E-Mail-Adresse",
            )

        # Parse subject/body from suggested_content or use overrides
        subject = subject_override
        body = body_override

        if not subject or not body:
            suggested = action.suggested_content or ""
            if suggested.startswith("Betreff:"):
                parts = suggested.split("\n\n", 1)
                if not subject:
                    subject = parts[0].replace("Betreff:", "").strip()
                if not body and len(parts) > 1:
                    body = parts[1]

        if not subject or not body:
            raise HTTPException(
                status_code=400,
                detail="Betreff und Inhalt erforderlich",
            )

        # Send the email using campaign service
        service = EmailCampaignService(db)

        # Create a quick campaign for this single email
        send_result = await service.send_single_email(
            tenant_id=tenant_id,
            to_email=contact.email,
            to_name=contact.name,
            subject=subject,
            body=body,
        )

        # Mark action as completed
        action.status = "completed"
        action.completed_at = datetime.utcnow()
        action.result = send_result

        # Update enrollment touch tracking
        if action.enrollment:
            action.enrollment.touch_count += 1
            action.enrollment.last_touch_at = datetime.utcnow()

        await db.commit()

        return {
            "action_id": action_id,
            "status": "completed",
            "result": send_result,
        }
    except HTTPException:
        raise
    except AppError as e:
        action.status = "failed"
        action.error_message = e.message
        await db.commit()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error executing engagement action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
