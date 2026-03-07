"""Post-Mail Module Router.

API endpoints for letter templates, letters, and batches.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.postmail.schemas import (
    BatchCreate,
    BatchExportResponse,
    BatchList,
    BatchResponse,
    LetterCreate,
    LetterList,
    LetterResponse,
    LetterUpdate,
    PostmailStats,
    RenderPreviewRequest,
    RenderPreviewResponse,
    TemplateCreate,
    TemplateList,
    TemplateResponse,
    TemplateUpdate,
)
from app.postmail.service import PostmailService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/postmail", tags=["postmail"])


# ============== Dependencies ==============


async def get_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PostmailService:
    """Get PostmailService instance."""
    return PostmailService(db, tenant_id)


# ============== Templates ==============


@router.get(
    "/templates",
    response_model=TemplateList,
    summary="List Templates",
    description="Get all letter templates.",
)
async def list_templates(
    active_only: bool = Query(False, description="Only active templates"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PostmailService = Depends(get_service),
) -> TemplateList:
    """List all templates."""
    templates, total = await service.list_templates(
        active_only=active_only,
        limit=limit,
        offset=offset,
    )

    items = []
    for t in templates:
        items.append(
            TemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                format=t.format,
                content_html=t.content_html,
                header_html=t.header_html,
                footer_html=t.footer_html,
                preview_image=t.preview_image,
                is_active=t.is_active,
                created_at=t.created_at,
                updated_at=t.updated_at,
                letter_count=len(t.letters) if t.letters else 0,
            )
        )

    return TemplateList(items=items, total=total)


@router.post(
    "/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Template",
    description="Create a new letter template.",
)
async def create_template(
    data: TemplateCreate,
    service: PostmailService = Depends(get_service),
) -> TemplateResponse:
    """Create a new template."""
    template = await service.create_template(
        name=data.name,
        content_html=data.content_html,
        description=data.description,
        format=data.format.value,
        header_html=data.header_html,
        footer_html=data.footer_html,
    )

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        format=template.format,
        content_html=template.content_html,
        header_html=template.header_html,
        footer_html=template.footer_html,
        preview_image=template.preview_image,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        letter_count=0,
    )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get Template",
    description="Get template details.",
)
async def get_template(
    template_id: int,
    service: PostmailService = Depends(get_service),
) -> TemplateResponse:
    """Get template by ID."""
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        format=template.format,
        content_html=template.content_html,
        header_html=template.header_html,
        footer_html=template.footer_html,
        preview_image=template.preview_image,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        letter_count=len(template.letters) if template.letters else 0,
    )


@router.put(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Update Template",
    description="Update a template.",
)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    service: PostmailService = Depends(get_service),
) -> TemplateResponse:
    """Update a template."""
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("format"):
        update_data["format"] = update_data["format"].value

    template = await service.update_template(template_id, **update_data)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        format=template.format,
        content_html=template.content_html,
        header_html=template.header_html,
        footer_html=template.footer_html,
        preview_image=template.preview_image,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        letter_count=len(template.letters) if template.letters else 0,
    )


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Template",
    description="Deactivate a template.",
)
async def delete_template(
    template_id: int,
    service: PostmailService = Depends(get_service),
) -> None:
    """Delete (deactivate) a template."""
    success = await service.delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")


@router.post(
    "/templates/preview",
    response_model=RenderPreviewResponse,
    summary="Preview Template",
    description="Render a template preview.",
)
async def preview_template(
    data: RenderPreviewRequest,
    service: PostmailService = Depends(get_service),
) -> RenderPreviewResponse:
    """Render template preview."""
    try:
        html, recipient = await service.render_preview(
            template_id=data.template_id,
            contact_id=data.contact_id,
            custom_data=data.custom_data,
        )
        return RenderPreviewResponse(html=html, recipient=recipient)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============== Letters ==============


@router.get(
    "/letters",
    response_model=LetterList,
    summary="List Letters",
    description="Get all letters.",
)
async def list_letters(
    status: str | None = Query(None, description="Filter by status"),
    batch_id: int | None = Query(None, description="Filter by batch"),
    contact_id: int | None = Query(None, description="Filter by contact"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PostmailService = Depends(get_service),
) -> LetterList:
    """List all letters."""
    letters, total = await service.list_letters(
        status=status,
        batch_id=batch_id,
        contact_id=contact_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for letter in letters:
        items.append(
            LetterResponse(
                id=letter.id,
                template_id=letter.template_id,
                template_name=letter.template.name if letter.template else None,
                contact_id=letter.contact_id,
                pipeline_id=letter.pipeline_id,
                batch_id=letter.batch_id,
                recipient_name=letter.recipient_name,
                recipient_company=letter.recipient_company,
                recipient_street=letter.recipient_street,
                recipient_zip=letter.recipient_zip,
                recipient_city=letter.recipient_city,
                recipient_country=letter.recipient_country,
                content_html=letter.content_html,
                pdf_path=letter.pdf_path,
                status=letter.status,
                queued_at=letter.queued_at,
                sent_at=letter.sent_at,
                delivered_at=letter.delivered_at,
                returned_at=letter.returned_at,
                return_reason=letter.return_reason,
                created_at=letter.created_at,
                updated_at=letter.updated_at,
            )
        )

    return LetterList(items=items, total=total)


@router.post(
    "/letters",
    response_model=LetterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Letter",
    description="Create a new letter.",
)
async def create_letter(
    data: LetterCreate,
    service: PostmailService = Depends(get_service),
) -> LetterResponse:
    """Create a new letter."""
    try:
        letter = await service.create_letter(
            template_id=data.template_id,
            recipient=data.recipient,
            contact_id=data.contact_id,
            pipeline_id=data.pipeline_id,
            content_html=data.content_html,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return LetterResponse(
        id=letter.id,
        template_id=letter.template_id,
        template_name=None,
        contact_id=letter.contact_id,
        pipeline_id=letter.pipeline_id,
        batch_id=letter.batch_id,
        recipient_name=letter.recipient_name,
        recipient_company=letter.recipient_company,
        recipient_street=letter.recipient_street,
        recipient_zip=letter.recipient_zip,
        recipient_city=letter.recipient_city,
        recipient_country=letter.recipient_country,
        content_html=letter.content_html,
        pdf_path=letter.pdf_path,
        status=letter.status,
        queued_at=letter.queued_at,
        sent_at=letter.sent_at,
        delivered_at=letter.delivered_at,
        returned_at=letter.returned_at,
        return_reason=letter.return_reason,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


@router.post(
    "/letters/from-contact/{contact_id}",
    response_model=LetterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Letter from Contact",
    description="Create a letter using contact's address.",
)
async def create_letter_from_contact(
    contact_id: int,
    template_id: int = Query(..., description="Template to use"),
    pipeline_id: int | None = Query(None, description="Optional pipeline"),
    service: PostmailService = Depends(get_service),
) -> LetterResponse:
    """Create letter from contact."""
    try:
        letter = await service.create_letter_from_contact(
            template_id=template_id,
            contact_id=contact_id,
            pipeline_id=pipeline_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return LetterResponse(
        id=letter.id,
        template_id=letter.template_id,
        template_name=None,
        contact_id=letter.contact_id,
        pipeline_id=letter.pipeline_id,
        batch_id=letter.batch_id,
        recipient_name=letter.recipient_name,
        recipient_company=letter.recipient_company,
        recipient_street=letter.recipient_street,
        recipient_zip=letter.recipient_zip,
        recipient_city=letter.recipient_city,
        recipient_country=letter.recipient_country,
        content_html=letter.content_html,
        pdf_path=letter.pdf_path,
        status=letter.status,
        queued_at=letter.queued_at,
        sent_at=letter.sent_at,
        delivered_at=letter.delivered_at,
        returned_at=letter.returned_at,
        return_reason=letter.return_reason,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


@router.get(
    "/letters/{letter_id}",
    response_model=LetterResponse,
    summary="Get Letter",
    description="Get letter details.",
)
async def get_letter(
    letter_id: int,
    service: PostmailService = Depends(get_service),
) -> LetterResponse:
    """Get letter by ID."""
    letter = await service.get_letter(letter_id)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    return LetterResponse(
        id=letter.id,
        template_id=letter.template_id,
        template_name=letter.template.name if letter.template else None,
        contact_id=letter.contact_id,
        pipeline_id=letter.pipeline_id,
        batch_id=letter.batch_id,
        recipient_name=letter.recipient_name,
        recipient_company=letter.recipient_company,
        recipient_street=letter.recipient_street,
        recipient_zip=letter.recipient_zip,
        recipient_city=letter.recipient_city,
        recipient_country=letter.recipient_country,
        content_html=letter.content_html,
        pdf_path=letter.pdf_path,
        status=letter.status,
        queued_at=letter.queued_at,
        sent_at=letter.sent_at,
        delivered_at=letter.delivered_at,
        returned_at=letter.returned_at,
        return_reason=letter.return_reason,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


@router.put(
    "/letters/{letter_id}",
    response_model=LetterResponse,
    summary="Update Letter",
    description="Update a letter.",
)
async def update_letter(
    letter_id: int,
    data: LetterUpdate,
    service: PostmailService = Depends(get_service),
) -> LetterResponse:
    """Update a letter."""
    update_data = data.model_dump(exclude_unset=True)
    if update_data.get("status"):
        update_data["status"] = update_data["status"].value

    letter = await service.update_letter(letter_id, **update_data)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")

    return LetterResponse(
        id=letter.id,
        template_id=letter.template_id,
        template_name=letter.template.name if letter.template else None,
        contact_id=letter.contact_id,
        pipeline_id=letter.pipeline_id,
        batch_id=letter.batch_id,
        recipient_name=letter.recipient_name,
        recipient_company=letter.recipient_company,
        recipient_street=letter.recipient_street,
        recipient_zip=letter.recipient_zip,
        recipient_city=letter.recipient_city,
        recipient_country=letter.recipient_country,
        content_html=letter.content_html,
        pdf_path=letter.pdf_path,
        status=letter.status,
        queued_at=letter.queued_at,
        sent_at=letter.sent_at,
        delivered_at=letter.delivered_at,
        returned_at=letter.returned_at,
        return_reason=letter.return_reason,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


@router.post(
    "/letters/{letter_id}/approve",
    response_model=LetterResponse,
    summary="Approve Letter",
    description="Approve a draft letter for sending.",
)
async def approve_letter(
    letter_id: int,
    service: PostmailService = Depends(get_service),
) -> LetterResponse:
    """Approve a draft letter."""
    letter = await service.approve_letter(letter_id)
    if not letter:
        raise HTTPException(
            status_code=400, detail="Letter not found or not in draft status"
        )

    return LetterResponse(
        id=letter.id,
        template_id=letter.template_id,
        template_name=letter.template.name if letter.template else None,
        contact_id=letter.contact_id,
        pipeline_id=letter.pipeline_id,
        batch_id=letter.batch_id,
        recipient_name=letter.recipient_name,
        recipient_company=letter.recipient_company,
        recipient_street=letter.recipient_street,
        recipient_zip=letter.recipient_zip,
        recipient_city=letter.recipient_city,
        recipient_country=letter.recipient_country,
        content_html=letter.content_html,
        pdf_path=letter.pdf_path,
        status=letter.status,
        queued_at=letter.queued_at,
        sent_at=letter.sent_at,
        delivered_at=letter.delivered_at,
        returned_at=letter.returned_at,
        return_reason=letter.return_reason,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


@router.post(
    "/letters/{letter_id}/generate-pdf",
    response_model=dict,
    summary="Generate PDF",
    description="Generate PDF for a letter.",
)
async def generate_letter_pdf(
    letter_id: int,
    service: PostmailService = Depends(get_service),
) -> dict:
    """Generate PDF for letter."""
    try:
        pdf_path = await service.generate_pdf(letter_id)
        return {"pdf_path": pdf_path}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/letters/{letter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Letter",
    description="Delete a draft letter.",
)
async def delete_letter(
    letter_id: int,
    service: PostmailService = Depends(get_service),
) -> None:
    """Delete a draft letter."""
    success = await service.delete_letter(letter_id)
    if not success:
        raise HTTPException(
            status_code=400, detail="Letter not found or not in draft status"
        )


# ============== Batches ==============


@router.get(
    "/batches",
    response_model=BatchList,
    summary="List Batches",
    description="Get all batches.",
)
async def list_batches(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: PostmailService = Depends(get_service),
) -> BatchList:
    """List all batches."""
    batches, total = await service.list_batches(
        status=status,
        limit=limit,
        offset=offset,
    )

    items = [
        BatchResponse(
            id=b.id,
            name=b.name,
            letter_count=b.letter_count,
            export_format=b.export_format,
            export_path=b.export_path,
            status=b.status,
            exported_at=b.exported_at,
            sent_at=b.sent_at,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        for b in batches
    ]

    return BatchList(items=items, total=total)


@router.post(
    "/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Batch",
    description="Create a new batch from letters.",
)
async def create_batch(
    data: BatchCreate,
    service: PostmailService = Depends(get_service),
) -> BatchResponse:
    """Create a new batch."""
    batch = await service.create_batch(
        name=data.name,
        letter_ids=data.letter_ids,
    )

    return BatchResponse(
        id=batch.id,
        name=batch.name,
        letter_count=batch.letter_count,
        export_format=batch.export_format,
        export_path=batch.export_path,
        status=batch.status,
        exported_at=batch.exported_at,
        sent_at=batch.sent_at,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


@router.get(
    "/batches/{batch_id}",
    response_model=BatchResponse,
    summary="Get Batch",
    description="Get batch details.",
)
async def get_batch(
    batch_id: int,
    service: PostmailService = Depends(get_service),
) -> BatchResponse:
    """Get batch by ID."""
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return BatchResponse(
        id=batch.id,
        name=batch.name,
        letter_count=batch.letter_count,
        export_format=batch.export_format,
        export_path=batch.export_path,
        status=batch.status,
        exported_at=batch.exported_at,
        sent_at=batch.sent_at,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


@router.post(
    "/batches/{batch_id}/export",
    response_model=BatchExportResponse,
    summary="Export Batch",
    description="Export batch as CSV for lettershop.",
)
async def export_batch(
    batch_id: int,
    service: PostmailService = Depends(get_service),
) -> BatchExportResponse:
    """Export batch as CSV."""
    try:
        export_path = await service.export_batch(batch_id)
        batch = await service.get_batch(batch_id)
        return BatchExportResponse(
            batch_id=batch_id,
            export_path=export_path,
            letter_count=batch.letter_count if batch else 0,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/batches/{batch_id}/mark-sent",
    response_model=BatchResponse,
    summary="Mark Batch Sent",
    description="Mark batch and all letters as sent.",
)
async def mark_batch_sent(
    batch_id: int,
    service: PostmailService = Depends(get_service),
) -> BatchResponse:
    """Mark batch as sent."""
    batch = await service.mark_batch_sent(batch_id)
    if not batch:
        raise HTTPException(
            status_code=400, detail="Batch not found or not in exported status"
        )

    return BatchResponse(
        id=batch.id,
        name=batch.name,
        letter_count=batch.letter_count,
        export_format=batch.export_format,
        export_path=batch.export_path,
        status=batch.status,
        exported_at=batch.exported_at,
        sent_at=batch.sent_at,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


# ============== Stats ==============


@router.get(
    "/stats",
    response_model=PostmailStats,
    summary="Get Stats",
    description="Get post-mail statistics.",
)
async def get_stats(
    service: PostmailService = Depends(get_service),
) -> PostmailStats:
    """Get post-mail statistics."""
    stats = await service.get_stats()
    return PostmailStats(**stats)
