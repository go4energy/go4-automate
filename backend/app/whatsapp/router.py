"""WhatsApp Business API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError
from app.utils.dependencies import get_current_tenant_id
from app.whatsapp.config_schema import whatsapp_interface
from app.whatsapp.schemas import (
    CampaignScheduleRequest,
    CampaignTemplateVariablesRequest,
    WhatsAppAccountCreate,
    WhatsAppAccountListResponse,
    WhatsAppAccountResponse,
    WhatsAppAccountUpdate,
    WhatsAppCampaignCreate,
    WhatsAppCampaignListResponse,
    WhatsAppCampaignRecipientResponse,
    WhatsAppCampaignResponse,
    WhatsAppCampaignStats,
    WhatsAppCampaignUpdate,
    WhatsAppConversationCreate,
    WhatsAppConversationListResponse,
    WhatsAppConversationResponse,
    WhatsAppConversationWithMessages,
    WhatsAppDashboard,
    WhatsAppMessageResponse,
    WhatsAppMessageSend,
    WhatsAppTemplateListResponse,
    WhatsAppTemplatePreviewRequest,
    WhatsAppTemplatePreviewResponse,
    WhatsAppTemplateResponse,
)
from app.whatsapp.service import (
    WhatsAppAccountService,
    WhatsAppCampaignService,
    WhatsAppConversationService,
    WhatsAppTemplateService,
)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Register module interface endpoints
whatsapp_interface.register_endpoints(router)


# ==================== Dashboard ====================


@router.get("/dashboard", response_model=WhatsAppDashboard)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get WhatsApp dashboard overview."""
    from datetime import datetime, timedelta

    from sqlalchemy import func, select

    from app.whatsapp.models import (
        WhatsAppAccount,
        WhatsAppCampaign,
        WhatsAppConversation,
        WhatsAppMessage,
    )

    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    cutoff_7d = datetime.utcnow() - timedelta(days=7)

    # Accounts
    total_accounts = await db.execute(
        select(func.count(WhatsAppAccount.id)).where(
            WhatsAppAccount.tenant_id == tenant_id
        )
    )
    active_accounts = await db.execute(
        select(func.count(WhatsAppAccount.id)).where(
            WhatsAppAccount.tenant_id == tenant_id,
            WhatsAppAccount.status == "active",
        )
    )

    # Conversations
    total_conversations = await db.execute(
        select(func.count(WhatsAppConversation.id)).where(
            WhatsAppConversation.tenant_id == tenant_id
        )
    )
    open_conversations = await db.execute(
        select(func.count(WhatsAppConversation.id)).where(
            WhatsAppConversation.tenant_id == tenant_id,
            WhatsAppConversation.status == "open",
        )
    )

    # Campaigns
    total_campaigns = await db.execute(
        select(func.count(WhatsAppCampaign.id)).where(
            WhatsAppCampaign.tenant_id == tenant_id
        )
    )
    sent_campaigns = await db.execute(
        select(func.count(WhatsAppCampaign.id)).where(
            WhatsAppCampaign.tenant_id == tenant_id,
            WhatsAppCampaign.status == "sent",
        )
    )

    # Messages 24h
    messages_sent_24h = await db.execute(
        select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.direction == "outbound",
            WhatsAppMessage.created_at >= cutoff_24h,
        )
    )
    messages_received_24h = await db.execute(
        select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.direction == "inbound",
            WhatsAppMessage.created_at >= cutoff_24h,
        )
    )

    # Delivery/Read rates 7d
    sent_7d = await db.execute(
        select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.direction == "outbound",
            WhatsAppMessage.created_at >= cutoff_7d,
        )
    )
    delivered_7d = await db.execute(
        select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.direction == "outbound",
            WhatsAppMessage.delivered_at.isnot(None),
            WhatsAppMessage.created_at >= cutoff_7d,
        )
    )
    read_7d = await db.execute(
        select(func.count(WhatsAppMessage.id)).where(
            WhatsAppMessage.tenant_id == tenant_id,
            WhatsAppMessage.direction == "outbound",
            WhatsAppMessage.read_at.isnot(None),
            WhatsAppMessage.created_at >= cutoff_7d,
        )
    )

    sent_count = sent_7d.scalar() or 0
    delivered_count = delivered_7d.scalar() or 0
    read_count = read_7d.scalar() or 0

    delivery_rate = (
        round((delivered_count / sent_count) * 100, 2) if sent_count > 0 else 0.0
    )
    read_rate = (
        round((read_count / delivered_count) * 100, 2) if delivered_count > 0 else 0.0
    )

    return WhatsAppDashboard(
        total_accounts=total_accounts.scalar() or 0,
        active_accounts=active_accounts.scalar() or 0,
        total_conversations=total_conversations.scalar() or 0,
        open_conversations=open_conversations.scalar() or 0,
        total_campaigns=total_campaigns.scalar() or 0,
        sent_campaigns=sent_campaigns.scalar() or 0,
        messages_sent_24h=messages_sent_24h.scalar() or 0,
        messages_received_24h=messages_received_24h.scalar() or 0,
        delivery_rate_7d=delivery_rate,
        read_rate_7d=read_rate,
    )


# ==================== Accounts ====================


@router.get("/accounts", response_model=list[WhatsAppAccountListResponse])
async def list_accounts(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List WhatsApp accounts."""
    service = WhatsAppAccountService(db, tenant_id)
    return await service.list_accounts(status=status)


@router.post(
    "/accounts",
    response_model=WhatsAppAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    data: WhatsAppAccountCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a new WhatsApp account."""
    try:
        service = WhatsAppAccountService(db, tenant_id)
        return await service.create(data)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/accounts/{account_id}", response_model=WhatsAppAccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a WhatsApp account."""
    try:
        service = WhatsAppAccountService(db, tenant_id)
        return await service.get_by_id(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.put("/accounts/{account_id}", response_model=WhatsAppAccountResponse)
async def update_account(
    account_id: int,
    data: WhatsAppAccountUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a WhatsApp account."""
    try:
        service = WhatsAppAccountService(db, tenant_id)
        return await service.update(account_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a WhatsApp account."""
    try:
        service = WhatsAppAccountService(db, tenant_id)
        await service.delete(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post("/accounts/{account_id}/verify")
async def verify_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Verify account credentials with Meta API."""
    try:
        service = WhatsAppAccountService(db, tenant_id)
        return await service.verify_credentials(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ==================== Templates ====================


@router.get("/templates", response_model=list[WhatsAppTemplateListResponse])
async def list_templates(
    account_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List WhatsApp templates."""
    service = WhatsAppTemplateService(db, tenant_id)
    return await service.list_templates(account_id=account_id, status=status)


@router.post("/templates/sync", response_model=list[WhatsAppTemplateResponse])
async def sync_templates(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Sync templates from Meta for an account."""
    try:
        service = WhatsAppTemplateService(db, tenant_id)
        return await service.sync_templates(account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/templates/{template_id}", response_model=WhatsAppTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a WhatsApp template."""
    try:
        service = WhatsAppTemplateService(db, tenant_id)
        return await service.get_by_id(template_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post(
    "/templates/{template_id}/preview",
    response_model=WhatsAppTemplatePreviewResponse,
)
async def preview_template(
    template_id: int,
    data: WhatsAppTemplatePreviewRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Preview a template with variables."""
    try:
        service = WhatsAppTemplateService(db, tenant_id)
        return await service.preview_template(template_id, data.variables)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


# ==================== Conversations ====================


@router.get("/conversations", response_model=list[WhatsAppConversationListResponse])
async def list_conversations(
    account_id: int | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List WhatsApp conversations (inbox)."""
    service = WhatsAppConversationService(db, tenant_id)
    return await service.list_conversations(
        account_id=account_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/conversations",
    response_model=WhatsAppConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: WhatsAppConversationCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Start a new conversation."""
    try:
        service = WhatsAppConversationService(db, tenant_id)
        return await service.get_or_create(
            account_id=data.account_id,
            phone=data.phone,
            contact_id=data.contact_id,
            contact_name=data.contact_name,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get(
    "/conversations/{conversation_id}",
    response_model=WhatsAppConversationWithMessages,
)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a conversation with messages."""
    try:
        service = WhatsAppConversationService(db, tenant_id)
        return await service.get_by_id(conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=WhatsAppMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: int,
    data: WhatsAppMessageSend,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Send a message in a conversation."""
    try:
        service = WhatsAppConversationService(db, tenant_id)
        return await service.send_message(conversation_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=WhatsAppConversationResponse,
)
async def mark_conversation_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Mark a conversation as read."""
    try:
        service = WhatsAppConversationService(db, tenant_id)
        return await service.mark_as_read(conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


# ==================== Campaigns ====================


@router.get("/campaigns", response_model=list[WhatsAppCampaignListResponse])
async def list_campaigns(
    status: str | None = None,
    pipeline_id: int | None = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List WhatsApp campaigns."""
    service = WhatsAppCampaignService(db, tenant_id)
    return await service.list_campaigns(
        status=status, limit=limit, offset=offset, pipeline_id=pipeline_id
    )


@router.post(
    "/campaigns",
    response_model=WhatsAppCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: WhatsAppCampaignCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Create a new campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.create(data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/campaigns/{campaign_id}", response_model=WhatsAppCampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get a campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.get_by_id(campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.put("/campaigns/{campaign_id}", response_model=WhatsAppCampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: WhatsAppCampaignUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update a campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.update(campaign_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Delete a campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        await service.delete(campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/campaigns/{campaign_id}/generate-recipients")
async def generate_campaign_recipients(
    campaign_id: int,
    data: CampaignTemplateVariablesRequest | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Generate recipients for a campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        count = await service.generate_recipients(
            campaign_id,
            default_variables=data.default_variables if data else None,
        )
        return {"count": count}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/campaigns/{campaign_id}/send", response_model=WhatsAppCampaignResponse)
async def send_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Send a campaign immediately."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.send_campaign(campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post(
    "/campaigns/{campaign_id}/schedule",
    response_model=WhatsAppCampaignResponse,
)
async def schedule_campaign(
    campaign_id: int,
    data: CampaignScheduleRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Schedule a campaign."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.schedule_campaign(campaign_id, data.scheduled_at)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.get("/campaigns/{campaign_id}/stats", response_model=WhatsAppCampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get campaign statistics."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.get_stats(campaign_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get(
    "/campaigns/{campaign_id}/recipients",
    response_model=list[WhatsAppCampaignRecipientResponse],
)
async def list_campaign_recipients(
    campaign_id: int,
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """List campaign recipients."""
    try:
        service = WhatsAppCampaignService(db, tenant_id)
        return await service.list_recipients(
            campaign_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


# ==================== Engagement Brain Integration ====================


@router.get("/engagement/actions")
async def get_engagement_actions(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Get pending engagement actions for WhatsApp.

    These are actions created by the Engagement Brain that need to be
    processed by the WhatsApp module.
    """
    from loguru import logger
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
                PendingAction.module == "whatsapp",
            )
        )

        if status_filter:
            query = query.where(PendingAction.status == status_filter)
        else:
            # Default: Show actions that need attention
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
                "contact_phone": a.contact.phone if a.contact else None,
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
    Generate content for a pending WhatsApp action using LLM.

    This uses the pipeline's stored prompts and contact context to generate
    personalized WhatsApp content.
    """
    from loguru import logger
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction
    from app.services.llm import LLMService

    try:
        # Get the action
        result = await db.execute(
            select(PendingAction)
            .options(
                selectinload(PendingAction.contact),
                selectinload(PendingAction.pipeline),
            )
            .where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
                PendingAction.module == "whatsapp",
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(status_code=404, detail="Aktion nicht gefunden")

        context = action.context or {}
        pipeline = action.pipeline
        contact = action.contact

        # Build content generation prompt
        prompt = f"""
Schreibe eine WhatsApp-Nachricht für einen Geschäftskontakt.
Die Nachricht sollte freundlich und persönlich sein, aber professionell.

EMPFÄNGER:
- Name: {context.get('contact_name', contact.name if contact else 'Unbekannt')}
- Position: {context.get('contact_position', '')}
- Unternehmen: {context.get('contact_company', '')}

KONTEXT:
- Produkt: {context.get('product_name', pipeline.product_name if pipeline else '')}
- Ziel: {context.get('goal', pipeline.goal if pipeline else '')}
- Tonalität: {context.get('tone_of_voice', pipeline.tone_of_voice if pipeline else 'professionell')}
- Bisherige Kontakte: {context.get('touch_count', 0)}

Regeln:
- Kurz und prägnant (max 160 Zeichen ideal für WhatsApp)
- Persönliche Ansprache
- Klarer Call-to-Action

Antworte NUR mit dem Nachrichtentext, keine Erklärungen.
"""

        llm = LLMService()
        content = await llm.generate(task="content", prompt=prompt)

        # Update the action with the generated content
        action.suggested_content = content
        await db.commit()

        return {
            "action_id": action_id,
            "generated_content": content,
            "action_type": action.action_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating action content")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/engagement/actions/{action_id}/execute")
async def execute_engagement_action(
    action_id: int,
    content_override: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Execute an engagement action via WhatsApp.

    This will:
    1. Send the WhatsApp message
    2. Log the activity
    3. Mark the action as completed
    """
    from datetime import datetime

    from loguru import logger
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.engagement.models import PendingAction
    from app.whatsapp.models import WhatsAppConversation
    from app.whatsapp.schemas import WhatsAppMessageSend, WhatsAppTextMessage

    try:
        # Get the action
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
                PendingAction.module == "whatsapp",
                PendingAction.status.in_(["approved", "pending"]),
            )
        )
        action = result.scalar_one_or_none()

        if not action:
            raise HTTPException(
                status_code=404,
                detail="Aktion nicht gefunden oder nicht ausführbar",
            )

        # Get content to send
        content = content_override or action.suggested_content
        if not content:
            raise HTTPException(
                status_code=400,
                detail="Kein Inhalt für die Aktion vorhanden",
            )

        # Get conversation from context or find by contact phone
        conversation_id = action.context.get("conversation_id") if action.context else None

        if not conversation_id:
            # Try to find conversation by contact phone
            phone = action.context.get("phone") if action.context else None
            if not phone and action.contact:
                phone = action.contact.phone

            if phone:
                conv_result = await db.execute(
                    select(WhatsAppConversation).where(
                        WhatsAppConversation.tenant_id == tenant_id,
                        WhatsAppConversation.phone == phone,
                    )
                )
                conversation = conv_result.scalar_one_or_none()
                if conversation:
                    conversation_id = conversation.id

        if not conversation_id:
            raise HTTPException(
                status_code=400,
                detail="Keine WhatsApp-Konversation für den Kontakt vorhanden",
            )

        # Send message
        service = WhatsAppConversationService(db, tenant_id)
        message = await service.send_message(
            conversation_id,
            WhatsAppMessageSend(
                message_type="text",
                text=WhatsAppTextMessage(body=content),
            ),
        )

        result_data = {
            "message_id": message.id,
            "wamid": message.wamid,
            "status": message.status,
        }

        # Mark action as completed
        action.status = "completed"
        action.completed_at = datetime.utcnow()
        action.result = result_data

        # Update enrollment touch tracking
        if action.enrollment:
            action.enrollment.touch_count += 1
            action.enrollment.last_touch_at = datetime.utcnow()

        await db.commit()

        return {
            "action_id": action_id,
            "status": "completed",
            "result": result_data,
        }
    except HTTPException:
        raise
    except AppError as e:
        # Mark action as failed
        action.status = "failed"
        action.error_message = e.message
        await db.commit()
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Error executing engagement action")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
