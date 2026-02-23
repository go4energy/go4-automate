"""Collector API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.config_schema import collector_interface
from app.collector.schemas import (
    AnalyzeFindingResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    ChangeDetectionResponse,
    CollectorFindingListItem,
    CollectorFindingResponse,
    CollectorFindingUpdate,
    CollectorGroupCreate,
    CollectorGroupListItem,
    CollectorGroupResponse,
    CollectorGroupUpdate,
    CollectorRunRequest,
    CollectorRunResponse,
    CollectorSourceCreate,
    CollectorSourceResponse,
    CollectorSourceUpdate,
    CollectorTopicCreate,
    CollectorTopicDetailResponse,
    CollectorTopicListItem,
    CollectorTopicResponse,
    CollectorTopicUpdate,
    FindingImport,
    GroupPromptAddRequest,
    GroupPromptAddResponse,
    GroupPromptRunResponse,
    InboxItemCreate,
    PageSnapshotResponse,
    TopicGenerateRequest,
)
from app.collector.service import CollectorService
from app.creator.schemas import CreatorPieceResponse
from app.database import get_db
from app.exceptions import AppError
from app.services.upload import UploadService
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/collector", tags=["collector"])

# Register standardized module interface endpoints
collector_interface.register_endpoints(router)


# --- Groups ---


@router.post(
    "/groups",
    response_model=CollectorGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_group(
    data: CollectorGroupCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorGroupResponse:
    """Create a new collector group."""
    try:
        service = CollectorService(db)
        return await service.create_group(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/groups", response_model=list[CollectorGroupListItem])
async def list_groups(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[CollectorGroupListItem]:
    """List collector groups with counts."""
    try:
        service = CollectorService(db)
        return await service.list_groups(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_groups")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/groups/{group_id}", response_model=CollectorGroupResponse)
async def get_group(
    group_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorGroupResponse:
    """Get a single collector group."""
    try:
        service = CollectorService(db)
        return await service.get_group(tenant_id, group_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/groups/{group_id}", response_model=CollectorGroupResponse)
async def update_group(
    group_id: int,
    data: CollectorGroupUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorGroupResponse:
    """Update a collector group."""
    try:
        service = CollectorService(db)
        return await service.update_group(tenant_id, group_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a collector group."""
    try:
        service = CollectorService(db)
        await service.delete_group(tenant_id, group_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_group")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Group Prompts ---


@router.post(
    "/groups/{group_id}/prompts",
    response_model=GroupPromptAddResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_group_prompt(
    group_id: int,
    data: GroupPromptAddRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> GroupPromptAddResponse:
    """Add a new prompt to a group."""
    try:
        service = CollectorService(db)
        return await service.add_group_prompt(
            tenant_id, group_id, data.purpose, source_slug=data.source_slug
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_group_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/groups/{group_id}/prompts/{prompt_slug}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_group_prompt(
    group_id: int,
    prompt_slug: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a prompt from a group."""
    try:
        service = CollectorService(db)
        await service.remove_group_prompt(tenant_id, group_id, prompt_slug)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in remove_group_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/groups/{group_id}/prompts/{prompt_slug}/run",
    response_model=GroupPromptRunResponse,
)
async def run_group_prompt(
    group_id: int,
    prompt_slug: str,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> GroupPromptRunResponse:
    """Run a specific prompt for a group's findings."""
    try:
        service = CollectorService(db)
        return await service.run_group_prompt(
            tenant_id, group_id, prompt_slug, tenant_config
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_group_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Sources ---


@router.post(
    "/sources",
    response_model=CollectorSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    data: CollectorSourceCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorSourceResponse:
    """Create a new collector source."""
    try:
        service = CollectorService(db)
        return await service.create_source(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sources", response_model=list[CollectorSourceResponse])
async def list_sources(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    source_type: str | None = Query(None),
    active: bool | None = Query(None),
    tag: str | None = Query(None),
    group_id: int | None = Query(None),
) -> list[CollectorSourceResponse]:
    """List collector sources."""
    try:
        service = CollectorService(db)
        return await service.list_sources(
            tenant_id,
            source_type=source_type,
            active=active,
            tag=tag,
            group_id=group_id,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sources/{source_id}", response_model=CollectorSourceResponse)
async def get_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorSourceResponse:
    """Get a single collector source."""
    try:
        service = CollectorService(db)
        return await service.get_source(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/sources/{source_id}", response_model=CollectorSourceResponse)
async def update_source(
    source_id: int,
    data: CollectorSourceUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorSourceResponse:
    """Update a collector source."""
    try:
        service = CollectorService(db)
        return await service.update_source(tenant_id, source_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a collector source."""
    try:
        service = CollectorService(db)
        await service.delete_source(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Collector Run ---


@router.post("/run", response_model=CollectorRunResponse)
async def run_collector(
    data: CollectorRunRequest | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> CollectorRunResponse:
    """Trigger a collector run (n8n calls this)."""
    try:
        service = CollectorService(db)
        source_id = data.source_id if data else None
        return await service.run_collector(tenant_id, source_id, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_collector")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Content Inbox ---


@router.post(
    "/inbox",
    response_model=CollectorFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_inbox_item(
    data: InboxItemCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorFindingResponse:
    """Create a finding from inbox (WhatsApp/Email)."""
    try:
        service = CollectorService(db)
        return await service.create_inbox_item(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_inbox_item")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Change Detection ---


@router.post(
    "/sources/{source_id}/detect-changes",
    response_model=ChangeDetectionResponse,
)
async def detect_changes(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChangeDetectionResponse:
    """Run change detection for a website source."""
    try:
        service = CollectorService(db)
        return await service.detect_changes(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in detect_changes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get(
    "/sources/{source_id}/snapshots",
    response_model=list[PageSnapshotResponse],
)
async def list_snapshots(
    source_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[PageSnapshotResponse]:
    """List page snapshots for a source."""
    try:
        service = CollectorService(db)
        return await service.list_snapshots(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_snapshots")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Findings ---


@router.post(
    "/findings",
    response_model=CollectorFindingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_finding(
    data: FindingImport,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorFindingResponse:
    """Import a finding from external source (n8n, webhook)."""
    try:
        service = CollectorService(db)
        return await service.import_finding(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in import_finding")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/findings", response_model=list[CollectorFindingListItem])
async def list_findings(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    source_id: int | None = Query(None),
    tag: str | None = Query(None),
    group_id: int | None = Query(None),
) -> list[CollectorFindingListItem]:
    """List collector findings."""
    try:
        service = CollectorService(db)
        return await service.list_findings(
            tenant_id,
            status=status_filter,
            source_id=source_id,
            tag=tag,
            group_id=group_id,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_findings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/findings/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_findings(
    data: BulkDeleteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkDeleteResponse:
    """Bulk delete findings by IDs."""
    try:
        service = CollectorService(db)
        deleted = await service.bulk_delete_findings(tenant_id, data.ids)
        return BulkDeleteResponse(deleted=deleted)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_delete_findings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/findings/{finding_id}/analyze",
    response_model=AnalyzeFindingResponse,
)
async def analyze_finding(
    finding_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeFindingResponse:
    """Analyze a single finding to generate topics."""
    try:
        service = CollectorService(db)
        topics = await service.analyze_finding(tenant_id, finding_id, tenant_config)
        return AnalyzeFindingResponse(topics_count=len(topics))
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in analyze_finding")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.patch("/findings/{finding_id}", response_model=CollectorFindingResponse)
async def update_finding(
    finding_id: int,
    data: CollectorFindingUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorFindingResponse:
    """Update a finding (status and/or group)."""
    try:
        service = CollectorService(db)
        return await service.update_finding(
            tenant_id, finding_id, status=data.status, group_id=data.group_id
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_finding")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Topics ---


@router.post(
    "/topics",
    response_model=CollectorTopicResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    data: CollectorTopicCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorTopicResponse:
    """Create a topic (Eigene Themen)."""
    try:
        service = CollectorService(db)
        return await service.create_topic(tenant_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/topics", response_model=list[CollectorTopicListItem])
async def list_topics(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = Query(None),
    tag: str | None = Query(None),
    group_id: int | None = Query(None),
) -> list[CollectorTopicListItem]:
    """List topics."""
    try:
        service = CollectorService(db)
        return await service.list_topics(
            tenant_id,
            status=status_filter,
            source_type=source_type,
            tag=tag,
            group_id=group_id,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_topics")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/topics/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_topics(
    data: BulkDeleteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkDeleteResponse:
    """Bulk delete topics by IDs."""
    try:
        service = CollectorService(db)
        deleted = await service.bulk_delete_topics(tenant_id, data.ids)
        return BulkDeleteResponse(deleted=deleted)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_delete_topics")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/topics/{topic_id}", response_model=CollectorTopicDetailResponse)
async def get_topic(
    topic_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorTopicDetailResponse:
    """Get a single topic with finding details."""
    try:
        service = CollectorService(db)
        return await service.get_topic_detail(tenant_id, topic_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/topics/{topic_id}/reanalyze", response_model=CollectorTopicResponse)
async def reanalyze_topic(
    topic_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> CollectorTopicResponse:
    """Re-analyze a topic using its linked prompt."""
    try:
        service = CollectorService(db)
        return await service.reanalyze_topic(tenant_id, topic_id, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in reanalyze_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/topics/{topic_id}", response_model=CollectorTopicResponse)
async def update_topic(
    topic_id: int,
    data: CollectorTopicUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CollectorTopicResponse:
    """Update a topic."""
    try:
        service = CollectorService(db)
        return await service.update_topic(tenant_id, topic_id, data)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a topic."""
    try:
        service = CollectorService(db)
        await service.delete_topic(tenant_id, topic_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/topics/{topic_id}/generate",
    response_model=CreatorPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_topic(
    topic_id: int,
    data: TopicGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> CreatorPieceResponse:
    """Generate content from a topic."""
    try:
        service = CollectorService(db)
        return await service.generate_from_topic(
            tenant_id, topic_id, data.platform, data.content_type, tenant_config
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_from_topic")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Image Upload ---


@router.post("/upload/image")
async def upload_image(
    file: UploadFile,
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Upload an image for content pieces."""
    try:
        service = UploadService()
        url = await service.save_image(tenant_id, file)
        return {"url": url}
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in upload_image")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
