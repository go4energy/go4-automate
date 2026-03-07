"""
Custom Audience Router

API endpoints for Meta Custom Audience management.
Handles CRUD operations, sync, and statistics.

Endpoints:
    GET    /audiences           - List audiences
    POST   /audiences           - Create audience
    GET    /audiences/{id}      - Get audience
    PUT    /audiences/{id}      - Update audience
    DELETE /audiences/{id}      - Delete audience
    POST   /audiences/{id}/sync - Sync audience
    GET    /audiences/logs      - Get sync logs
    GET    /audiences/stats     - Get statistics
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.engagement.audience_service import CustomAudienceService
from app.engagement.meta_schemas import (
    AudienceSyncLogList,
    AudienceSyncLogResponse,
    CustomAudienceCreate,
    CustomAudienceList,
    CustomAudienceResponse,
    CustomAudienceUpdate,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/audiences", tags=["custom-audiences"])


# ============== Dependency ==============


async def get_audience_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> CustomAudienceService:
    """
    Get CustomAudienceService instance for current tenant.

    Returns:
        CustomAudienceService configured for the tenant
    """
    return CustomAudienceService(db, tenant_id)


# ============== List & Create ==============


@router.get(
    "",
    response_model=CustomAudienceList,
    summary="List Custom Audiences",
    description="Get all Custom Audiences for the current tenant.",
)
async def list_audiences(
    pipeline_id: int | None = Query(None, description="Filter by pipeline"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: CustomAudienceService = Depends(get_audience_service),
) -> CustomAudienceList:
    """
    List all Custom Audiences.

    Supports filtering by pipeline and active status.
    Returns paginated results.
    """
    audiences, total = await service.list_audiences(
        pipeline_id=pipeline_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    items = []
    for audience in audiences:
        items.append(
            CustomAudienceResponse(
                id=audience.id,
                tenant_id=audience.tenant_id,
                name=audience.name,
                description=audience.description,
                meta_audience_id=audience.meta_audience_id,
                meta_audience_name=audience.meta_audience_name,
                pipeline_id=audience.pipeline_id,
                pipeline_name=audience.pipeline.name if audience.pipeline else None,
                segment_filter=audience.segment_filter,
                sync_mode=audience.sync_mode,
                is_active=audience.is_active,
                audience_size=audience.audience_size,
                last_sync_at=audience.last_sync_at,
                last_sync_count=audience.last_sync_count,
                last_sync_status=audience.last_sync_status,
                created_at=audience.created_at,
                updated_at=audience.updated_at,
            )
        )

    return CustomAudienceList(items=items, total=total)


@router.post(
    "",
    response_model=CustomAudienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Custom Audience",
    description="Create a new Custom Audience and optionally create it in Meta.",
)
async def create_audience(
    data: CustomAudienceCreate,
    service: CustomAudienceService = Depends(get_audience_service),
) -> CustomAudienceResponse:
    """
    Create a new Custom Audience.

    Creates the audience locally and optionally in Meta.
    The audience can then be synced with contacts.
    """
    try:
        audience = await service.create_audience(
            name=data.name,
            description=data.description,
            pipeline_id=data.pipeline_id,
            segment_filter=data.segment_filter.model_dump() if data.segment_filter else None,
            sync_mode=data.sync_mode.value,
            create_in_meta=data.create_in_meta,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return CustomAudienceResponse(
        id=audience.id,
        tenant_id=audience.tenant_id,
        name=audience.name,
        description=audience.description,
        meta_audience_id=audience.meta_audience_id,
        meta_audience_name=audience.meta_audience_name,
        pipeline_id=audience.pipeline_id,
        pipeline_name=audience.pipeline.name if audience.pipeline else None,
        segment_filter=audience.segment_filter,
        sync_mode=audience.sync_mode,
        is_active=audience.is_active,
        audience_size=audience.audience_size,
        last_sync_at=audience.last_sync_at,
        last_sync_count=audience.last_sync_count,
        last_sync_status=audience.last_sync_status,
        created_at=audience.created_at,
        updated_at=audience.updated_at,
    )


# ============== Get, Update, Delete ==============


@router.get(
    "/{audience_id}",
    response_model=CustomAudienceResponse,
    summary="Get Custom Audience",
    description="Get details of a specific Custom Audience.",
)
async def get_audience(
    audience_id: int,
    service: CustomAudienceService = Depends(get_audience_service),
) -> CustomAudienceResponse:
    """
    Get a Custom Audience by ID.

    Returns full audience details including sync status.
    """
    audience = await service.get_audience(audience_id)
    if not audience:
        raise HTTPException(status_code=404, detail="Audience not found")

    return CustomAudienceResponse(
        id=audience.id,
        tenant_id=audience.tenant_id,
        name=audience.name,
        description=audience.description,
        meta_audience_id=audience.meta_audience_id,
        meta_audience_name=audience.meta_audience_name,
        pipeline_id=audience.pipeline_id,
        pipeline_name=audience.pipeline.name if audience.pipeline else None,
        segment_filter=audience.segment_filter,
        sync_mode=audience.sync_mode,
        is_active=audience.is_active,
        audience_size=audience.audience_size,
        last_sync_at=audience.last_sync_at,
        last_sync_count=audience.last_sync_count,
        last_sync_status=audience.last_sync_status,
        created_at=audience.created_at,
        updated_at=audience.updated_at,
    )


@router.put(
    "/{audience_id}",
    response_model=CustomAudienceResponse,
    summary="Update Custom Audience",
    description="Update an existing Custom Audience configuration.",
)
async def update_audience(
    audience_id: int,
    data: CustomAudienceUpdate,
    service: CustomAudienceService = Depends(get_audience_service),
) -> CustomAudienceResponse:
    """
    Update a Custom Audience.

    Only provided fields will be updated.
    """
    try:
        audience = await service.update_audience(
            audience_id=audience_id,
            name=data.name,
            description=data.description,
            segment_filter=data.segment_filter.model_dump() if data.segment_filter else None,
            sync_mode=data.sync_mode.value if data.sync_mode else None,
            is_active=data.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return CustomAudienceResponse(
        id=audience.id,
        tenant_id=audience.tenant_id,
        name=audience.name,
        description=audience.description,
        meta_audience_id=audience.meta_audience_id,
        meta_audience_name=audience.meta_audience_name,
        pipeline_id=audience.pipeline_id,
        pipeline_name=audience.pipeline.name if audience.pipeline else None,
        segment_filter=audience.segment_filter,
        sync_mode=audience.sync_mode,
        is_active=audience.is_active,
        audience_size=audience.audience_size,
        last_sync_at=audience.last_sync_at,
        last_sync_count=audience.last_sync_count,
        last_sync_status=audience.last_sync_status,
        created_at=audience.created_at,
        updated_at=audience.updated_at,
    )


@router.delete(
    "/{audience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Custom Audience",
    description="Delete a Custom Audience. Optionally deletes in Meta too.",
)
async def delete_audience(
    audience_id: int,
    delete_in_meta: bool = Query(False, description="Also delete in Meta"),
    service: CustomAudienceService = Depends(get_audience_service),
) -> None:
    """
    Delete a Custom Audience.

    By default, only deletes locally. Set delete_in_meta=true to also
    delete the audience in Meta.
    """
    try:
        await service.delete_audience(audience_id, delete_in_meta=delete_in_meta)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============== Sync ==============


@router.post(
    "/{audience_id}/sync",
    response_model=AudienceSyncLogResponse,
    summary="Sync Custom Audience",
    description="Sync contacts to Meta Custom Audience.",
)
async def sync_audience(
    audience_id: int,
    service: CustomAudienceService = Depends(get_audience_service),
) -> AudienceSyncLogResponse:
    """
    Sync contacts to a Custom Audience.

    Fetches all contacts matching the segment filter,
    hashes their PII, and sends to Meta.
    """
    try:
        sync_log = await service.sync_audience(audience_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}") from e

    # Get audience name
    audience = await service.get_audience(audience_id)

    return AudienceSyncLogResponse(
        id=sync_log.id,
        audience_id=sync_log.audience_id,
        audience_name=audience.name if audience else None,
        operation=sync_log.operation,
        started_at=sync_log.started_at,
        completed_at=sync_log.completed_at,
        contacts_processed=sync_log.contacts_processed,
        contacts_added=sync_log.contacts_added,
        contacts_removed=sync_log.contacts_removed,
        contacts_failed=sync_log.contacts_failed,
        status=sync_log.status,
        error_message=sync_log.error_message,
    )


# ============== Sync Logs ==============


@router.get(
    "/logs",
    response_model=AudienceSyncLogList,
    summary="Get Sync Logs",
    description="Get sync operation logs for audiences.",
)
async def get_sync_logs(
    audience_id: int | None = Query(None, description="Filter by audience"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: CustomAudienceService = Depends(get_audience_service),
) -> AudienceSyncLogList:
    """
    Get sync operation logs.

    Returns paginated list of sync operations with statistics.
    """
    logs, total = await service.get_sync_logs(
        audience_id=audience_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for log in logs:
        items.append(
            AudienceSyncLogResponse(
                id=log.id,
                audience_id=log.audience_id,
                audience_name=log.audience.name if log.audience else None,
                operation=log.operation,
                started_at=log.started_at,
                completed_at=log.completed_at,
                contacts_processed=log.contacts_processed,
                contacts_added=log.contacts_added,
                contacts_removed=log.contacts_removed,
                contacts_failed=log.contacts_failed,
                status=log.status,
                error_message=log.error_message,
            )
        )

    return AudienceSyncLogList(items=items, total=total)
