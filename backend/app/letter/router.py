"""Letter Module Router.

API endpoints for letter templates, letters, batches, Letterxpress
operations (balance, send, sync), and cost statistics.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import AppError
from app.letter.letterxpress_client import LetterxpressError
from app.letter.models import Letter, LetterStatus
from app.letter.pdf_renderer import PdfRendererError, render_letter_pdf
from app.letter.schemas import (
    BatchCreate,
    BatchExportResponse,
    BatchList,
    BatchResponse,
    LetterCostStats,
    LetterCreate,
    LetterList,
    LetterResponse,
    LetterSendRequest,
    LetterSendResponse,
    LetterStats,
    LetterUpdate,
    LetterxpressBalanceResponse,
    RenderPreviewRequest,
    RenderPreviewResponse,
    TemplateCreate,
    TemplateList,
    TemplateResponse,
    TemplateUpdate,
)
from app.letter.service import LetterService
from app.letter.settings_service import (
    LETTER_PARAMS,
    LetterSettingsError,
    ensure_module_parameters,
    get_letter_settings,
    get_letterxpress_client,
    set_letter_setting,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/letter", tags=["letter"])


# ============== Dependencies ==============


async def get_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LetterService:
    """Get LetterService instance."""
    return LetterService(db, tenant_id)


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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    pipeline_id: int | None = Query(None, description="Filter by pipeline"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: LetterService = Depends(get_service),
) -> LetterList:
    """List all letters."""
    letters, total = await service.list_letters(
        status=status,
        batch_id=batch_id,
        contact_id=contact_id,
        pipeline_id=pipeline_id,
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    service: LetterService = Depends(get_service),
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
    response_model=LetterStats,
    summary="Get Stats",
    description="Get letter statistics.",
)
async def get_stats(
    service: LetterService = Depends(get_service),
) -> LetterStats:
    """Get letter statistics."""
    stats = await service.get_stats()
    return LetterStats(**stats)


@router.get(
    "/stats/costs",
    response_model=LetterCostStats,
    summary="Cost statistics",
    description="Aggregated provider cost over time, by pipeline and by day.",
)
async def get_cost_stats(
    period: str = Query("month", pattern="^(today|week|month|all)$"),
    mode: str = Query("all", pattern="^(test|live|all)$"),
    service: LetterService = Depends(get_service),
) -> LetterCostStats:
    """Aggregated letter costs."""
    data = await service.get_cost_stats(period=period, mode=mode)
    return LetterCostStats(**data)


# ============== Letterxpress / Provider ==============


@router.get(
    "/letterxpress/balance",
    response_model=LetterxpressBalanceResponse,
    summary="Letterxpress balance",
    description="Read current Letterxpress balance for this tenant.",
)
async def get_letterxpress_balance(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LetterxpressBalanceResponse:
    try:
        client = await get_letterxpress_client(db, tenant_id)
        info = await client.get_balance()
        return LetterxpressBalanceResponse(
            balance=float(info.balance),
            currency=info.currency,
            mode=client.mode,
        )
    except LetterSettingsError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except LetterxpressError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post(
    "/letters/{letter_id}/send",
    response_model=LetterSendResponse,
    summary="Submit a letter to Letterxpress",
    description=(
        "Renders the letter as PDF, submits it to Letterxpress in the "
        "requested mode (test/live), and updates the Letter record."
    ),
)
async def send_letter(
    letter_id: int,
    body: LetterSendRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LetterSendResponse:
    """Manual single-send (UI button)."""
    # Load letter + template
    q = (
        select(Letter)
        .options(selectinload(Letter.template))
        .where(Letter.id == letter_id, Letter.tenant_id == tenant_id)
    )
    letter = (await db.execute(q)).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Letter nicht gefunden")
    if letter.status not in (
        LetterStatus.DRAFT,
        LetterStatus.APPROVED,
        LetterStatus.QUEUED,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Letter im Status {letter.status!r} kann nicht gesendet werden.",
        )
    if not letter.template:
        raise HTTPException(status_code=400, detail="Letter hat kein Template.")

    try:
        pdf_bytes = render_letter_pdf(letter, letter.template, tenant_id=tenant_id)
        client = await get_letterxpress_client(db, tenant_id, override_mode=body.mode)
        result = await client.submit_letter(
            pdf_bytes,
            color="4",
            c4=1,
            filename_original=f"letter_{letter.id}.pdf",
        )
    except (LetterSettingsError, PdfRendererError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LetterxpressError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    letter.letterxpress_job_id = str(result.job_id)
    letter.send_mode = body.mode
    letter.provider_status = result.status
    letter.provider_cost_cents = int(round(float(result.amount_net) * 100))
    letter.provider_synced_at = datetime.now(UTC)
    letter.status = LetterStatus.SENT
    letter.sent_at = datetime.now(UTC)
    letter.updated_at = datetime.now(UTC)
    await db.commit()

    return LetterSendResponse(
        letter_id=letter.id,
        letterxpress_job_id=letter.letterxpress_job_id,
        provider_status=letter.provider_status or "",
        provider_cost_cents=letter.provider_cost_cents or 0,
        send_mode=letter.send_mode,
    )


@router.post(
    "/letters/{letter_id}/sync-status",
    response_model=LetterResponse,
    summary="Sync letter status from Letterxpress",
)
async def sync_letter_status(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LetterResponse:
    q = (
        select(Letter)
        .options(selectinload(Letter.template))
        .where(Letter.id == letter_id, Letter.tenant_id == tenant_id)
    )
    letter = (await db.execute(q)).scalar_one_or_none()
    if letter is None:
        raise HTTPException(status_code=404, detail="Letter nicht gefunden")
    if not letter.letterxpress_job_id:
        raise HTTPException(
            status_code=400,
            detail="Letter ist noch nicht an Letterxpress übergeben.",
        )

    try:
        client = await get_letterxpress_client(db, tenant_id)
        info = await client.get_job(int(letter.letterxpress_job_id))
    except LetterSettingsError as e:
        raise HTTPException(status_code=400, detail=e.message) from e
    except LetterxpressError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    letter.provider_status = info.status
    letter.provider_synced_at = datetime.now(UTC)
    if info.status == "done":
        letter.status = LetterStatus.DELIVERED
        letter.delivered_at = letter.delivered_at or datetime.now(UTC)
    elif info.status == "canceled":
        letter.status = LetterStatus.RETURNED
        letter.return_reason = letter.return_reason or "Provider canceled"
    await db.commit()

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
        letterxpress_job_id=letter.letterxpress_job_id,
        send_mode=letter.send_mode,
        provider_status=letter.provider_status,
        provider_cost_cents=letter.provider_cost_cents,
        provider_synced_at=letter.provider_synced_at,
        created_at=letter.created_at,
        updated_at=letter.updated_at,
    )


# ============== Settings (Letterxpress credentials, defaults) ==============


@router.get(
    "/settings",
    summary="List Letter module settings",
    description="Returns all module_parameters for the letter module. "
    "Password values are masked.",
)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    """Read settings for the Settings tab. Apikey is returned masked."""
    await ensure_module_parameters(db, tenant_id)
    settings = await get_letter_settings(db, tenant_id)
    return {
        "username": settings.username,
        "apikey_set": bool(settings.apikey),
        "apikey_masked": ("•" * 8 + settings.apikey[-4:]) if settings.apikey else "",
        "mode": settings.mode,
        "color": settings.color,
        "c4": settings.c4,
        "shipping": settings.shipping,
        "params_meta": [
            {
                "variable": p["variable"],
                "description": p["description"],
                "var_type": p["var_type"],
                "required": p["required"],
            }
            for p in LETTER_PARAMS
        ],
    }


@router.put(
    "/settings/{variable}",
    summary="Set a single Letter module setting",
)
async def update_setting(
    variable: str,
    value: dict,  # {"value": "..."}
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> dict:
    new_value = value.get("value")
    if new_value is None:
        raise HTTPException(status_code=400, detail="Feld 'value' fehlt im Body.")
    try:
        await set_letter_setting(db, tenant_id, variable, str(new_value))
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    await db.commit()
    return {"ok": True, "variable": variable}
