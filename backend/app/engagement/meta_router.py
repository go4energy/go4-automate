"""
Meta Conversions API Router

API endpoints for Meta (Facebook) Conversions API integration.
Handles setup, configuration, event sending, and statistics.

Endpoints:
    GET  /meta/status          - Quick status check
    GET  /meta/integration     - Get current integration
    POST /meta/integration     - Create/update integration
    PUT  /meta/integration     - Update integration
    DELETE /meta/integration   - Deactivate integration
    POST /meta/test-event      - Send a test event
    GET  /meta/events          - List conversion events
    GET  /meta/stats           - Get event statistics
    GET  /meta/setup-guide     - Get setup instructions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.engagement.meta_schemas import (
    ConversionEventList,
    ConversionEventResponse,
    EventStats,
    MetaIntegrationCreate,
    MetaIntegrationResponse,
    MetaIntegrationStatus,
    MetaIntegrationUpdate,
    SetupGuide,
    TestEventRequest,
    TestEventResponse,
)
from app.engagement.meta_service import MetaConversionsService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/meta", tags=["meta-conversions"])


# ============== Dependency ==============


async def get_meta_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> MetaConversionsService:
    """
    Get MetaConversionsService instance for current tenant.

    Returns:
        MetaConversionsService configured for the tenant
    """
    return MetaConversionsService(db, tenant_id)


# ============== Status ==============


@router.get(
    "/status",
    response_model=MetaIntegrationStatus,
    summary="Get integration status",
    description="Quick status check for Meta integration.",
)
async def get_status(
    service: MetaConversionsService = Depends(get_meta_service),
) -> MetaIntegrationStatus:
    """
    Get quick status of Meta integration.

    Returns basic info about configuration status and recent activity.
    """
    integration = await service.get_integration()

    if not integration:
        return MetaIntegrationStatus(
            is_configured=False,
            is_active=False,
            test_mode=False,
            pixel_id=None,
            last_event_at=None,
            events_today=0,
            success_rate=100.0,
        )

    # Get today's event count
    stats = await service.get_stats(days=1)

    return MetaIntegrationStatus(
        is_configured=True,
        is_active=integration.is_active,
        test_mode=integration.test_mode,
        pixel_id=integration.pixel_id,
        last_event_at=integration.last_event_at,
        events_today=stats.get("total_events", 0),
        success_rate=stats.get("success_rate", 100.0),
    )


# ============== Integration CRUD ==============


@router.get(
    "/integration",
    response_model=MetaIntegrationResponse | None,
    summary="Get current integration",
    description="Get the Meta integration configuration for the current tenant.",
)
async def get_integration(
    service: MetaConversionsService = Depends(get_meta_service),
) -> MetaIntegrationResponse | None:
    """
    Get Meta integration configuration.

    Returns the full configuration including masked access token.
    Returns None if not configured.
    """
    integration = await service.get_integration()

    if not integration:
        return None

    # Mask access token (show only last 4 characters)
    token = integration.access_token
    masked_token = f"{'*' * 20}{token[-4:]}" if len(token) > 4 else "*" * len(token)

    return MetaIntegrationResponse(
        id=integration.id,
        tenant_id=integration.tenant_id,
        pixel_id=integration.pixel_id,
        access_token_masked=masked_token,
        ad_account_id=integration.ad_account_id,
        is_active=integration.is_active,
        test_mode=integration.test_mode,
        last_event_at=integration.last_event_at,
        total_events_sent=integration.total_events_sent,
        total_events_failed=integration.total_events_failed,
        success_rate=integration.success_rate,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.post(
    "/integration",
    response_model=MetaIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update integration",
    description="Set up Meta Conversions API integration with Pixel ID and access token.",
)
async def create_integration(
    data: MetaIntegrationCreate,
    service: MetaConversionsService = Depends(get_meta_service),
) -> MetaIntegrationResponse:
    """
    Create or update Meta integration.

    If an integration already exists, it will be updated.
    Validates Pixel ID format (15-16 digits).

    Args:
        data: Integration configuration including Pixel ID and access token

    Returns:
        Created/updated integration

    Raises:
        400: Invalid Pixel ID format
    """
    try:
        integration = await service.create_integration(
            pixel_id=data.pixel_id,
            access_token=data.access_token,
            ad_account_id=data.ad_account_id,
            test_mode=data.test_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Mask token for response
    masked_token = f"{'*' * 20}{integration.access_token[-4:]}"

    return MetaIntegrationResponse(
        id=integration.id,
        tenant_id=integration.tenant_id,
        pixel_id=integration.pixel_id,
        access_token_masked=masked_token,
        ad_account_id=integration.ad_account_id,
        is_active=integration.is_active,
        test_mode=integration.test_mode,
        last_event_at=integration.last_event_at,
        total_events_sent=integration.total_events_sent,
        total_events_failed=integration.total_events_failed,
        success_rate=integration.success_rate,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.put(
    "/integration",
    response_model=MetaIntegrationResponse,
    summary="Update integration",
    description="Update existing Meta integration configuration.",
)
async def update_integration(
    data: MetaIntegrationUpdate,
    service: MetaConversionsService = Depends(get_meta_service),
) -> MetaIntegrationResponse:
    """
    Update Meta integration configuration.

    Only provided fields will be updated.

    Args:
        data: Fields to update

    Returns:
        Updated integration

    Raises:
        404: Integration not configured
        400: Invalid Pixel ID format
    """
    try:
        integration = await service.update_integration(
            pixel_id=data.pixel_id,
            access_token=data.access_token,
            ad_account_id=data.ad_account_id,
            is_active=data.is_active,
            test_mode=data.test_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Mask token for response
    masked_token = f"{'*' * 20}{integration.access_token[-4:]}"

    return MetaIntegrationResponse(
        id=integration.id,
        tenant_id=integration.tenant_id,
        pixel_id=integration.pixel_id,
        access_token_masked=masked_token,
        ad_account_id=integration.ad_account_id,
        is_active=integration.is_active,
        test_mode=integration.test_mode,
        last_event_at=integration.last_event_at,
        total_events_sent=integration.total_events_sent,
        total_events_failed=integration.total_events_failed,
        success_rate=integration.success_rate,
        created_at=integration.created_at,
        updated_at=integration.updated_at,
    )


@router.delete(
    "/integration",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate integration",
    description="Deactivate Meta integration (soft delete).",
)
async def delete_integration(
    service: MetaConversionsService = Depends(get_meta_service),
):
    """
    Deactivate Meta integration.

    Performs a soft delete - the integration can be reactivated later.
    Event logs are preserved.
    """
    deleted = await service.delete_integration()
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Meta integration not configured",
        )
    return None


# ============== Test Event ==============


@router.post(
    "/test-event",
    response_model=TestEventResponse,
    summary="Send test event",
    description="Send a test event to verify the integration is working.",
)
async def send_test_event(
    data: TestEventRequest,
    service: MetaConversionsService = Depends(get_meta_service),
) -> TestEventResponse:
    """
    Send a test event to Meta.

    Test events are marked with test_event_code and appear
    in the Meta Events Manager under "Test Events".

    Args:
        data: Test event configuration

    Returns:
        Result with success status and response details
    """
    result = await service.send_test_event(
        event_name=data.event_name.value,
        contact_id=data.contact_id,
        url=data.url,
    )

    return TestEventResponse(
        success=result.get("success", False),
        event_id=result.get("event_id"),
        message=result.get("message", ""),
        response_body=result.get("response_body"),
    )


# ============== Events ==============


@router.get(
    "/events",
    response_model=ConversionEventList,
    summary="List conversion events",
    description="Get paginated list of conversion events sent to Meta.",
)
async def list_events(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status (sent, failed, test)"),
    event_name: str | None = Query(None, description="Filter by event name"),
    contact_id: int | None = Query(None, description="Filter by contact"),
    days: int | None = Query(None, ge=1, le=90, description="Filter to last N days"),
    service: MetaConversionsService = Depends(get_meta_service),
) -> ConversionEventList:
    """
    Get paginated list of conversion events.

    Supports filtering by status, event type, contact, and time period.
    """
    offset = (page - 1) * page_size

    events, total = await service.get_events(
        limit=page_size,
        offset=offset,
        status=status,
        event_name=event_name,
        contact_id=contact_id,
        days=days,
    )

    items = []
    for event in events:
        contact_name = None
        if event.contact:
            contact_name = f"{event.contact.first_name or ''} {event.contact.last_name or ''}".strip()

        pipeline_name = event.pipeline.name if event.pipeline else None

        items.append(
            ConversionEventResponse(
                id=event.id,
                event_name=event.event_name,
                event_time=event.event_time,
                event_id=event.event_id,
                contact_id=event.contact_id,
                contact_name=contact_name,
                pipeline_id=event.pipeline_id,
                pipeline_name=pipeline_name,
                status=event.status,
                custom_data=event.custom_data,
                response_code=event.response_code,
                error_message=event.error_message,
                created_at=event.created_at,
                sent_at=event.sent_at,
            )
        )

    return ConversionEventList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=ConversionEventResponse,
    summary="Get event details",
    description="Get details of a specific conversion event.",
)
async def get_event(
    event_id: int,
    service: MetaConversionsService = Depends(get_meta_service),
) -> ConversionEventResponse:
    """
    Get details of a specific conversion event.

    Args:
        event_id: Database ID of the event

    Returns:
        Event details including response from Meta
    """
    events, _ = await service.get_events(limit=1, offset=0)

    # Find by ID
    from sqlalchemy import select

    from app.engagement.meta_models import ConversionEvent

    result = await service.db.execute(
        select(ConversionEvent).where(
            ConversionEvent.id == event_id,
            ConversionEvent.tenant_id == service.tenant_id,
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    contact_name = None
    if event.contact:
        contact_name = f"{event.contact.first_name or ''} {event.contact.last_name or ''}".strip()

    pipeline_name = event.pipeline.name if event.pipeline else None

    return ConversionEventResponse(
        id=event.id,
        event_name=event.event_name,
        event_time=event.event_time,
        event_id=event.event_id,
        contact_id=event.contact_id,
        contact_name=contact_name,
        pipeline_id=event.pipeline_id,
        pipeline_name=pipeline_name,
        status=event.status,
        custom_data=event.custom_data,
        response_code=event.response_code,
        error_message=event.error_message,
        created_at=event.created_at,
        sent_at=event.sent_at,
    )


# ============== Statistics ==============


@router.get(
    "/stats",
    response_model=EventStats,
    summary="Get event statistics",
    description="Get statistics about conversion events for the specified period.",
)
async def get_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    service: MetaConversionsService = Depends(get_meta_service),
) -> EventStats:
    """
    Get event statistics.

    Returns totals, success rate, and daily breakdown.
    """
    stats = await service.get_stats(days=days)

    return EventStats(
        period_start=stats["period_start"],
        period_end=stats["period_end"],
        total_events=stats["total_events"],
        events_sent=stats["events_sent"],
        events_failed=stats["events_failed"],
        success_rate=stats["success_rate"],
        events_by_type=stats["events_by_type"],
        events_by_day=stats["events_by_day"],
    )


# ============== Setup Guide ==============


@router.get(
    "/setup-guide",
    response_model=SetupGuide,
    summary="Get setup instructions",
    description="Get step-by-step instructions for setting up Meta integration.",
)
async def get_setup_guide() -> SetupGuide:
    """
    Get setup instructions for Meta integration.

    Returns step-by-step guide for creating Pixel, System User, and access token.
    """
    return SetupGuide()
