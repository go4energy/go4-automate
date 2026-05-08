"""Customer Journey internal router - dashboard, leads, ref-codes, campaigns."""

import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.customer_journey.config_schema import customer_journey_interface
from app.customer_journey.models import JourneyEvent
from app.customer_journey.schemas import (
    BulkGenerateRequest,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    DashboardStats,
    ImportExecuteRequest,
    ImportPreviewRequest,
    ImportPreviewResponse,
    JourneyEventResponse,
    LeadListResponse,
    LeadWithEvents,
    MappableField,
    RefCodeCreate,
    RefCodeResponse,
    RefCodeUpdate,
)
from app.customer_journey.service import (
    BulkRefCodeCreate,
    CampaignService,
    DashboardService,
    EventService,
    RefCodeService,
)
from app.database import get_db
from app.exceptions import NotFoundError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/customer-journey", tags=["customer-journey"])

customer_journey_interface.register_endpoints(router)


# ============== Dashboard ==============


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Get dashboard overview stats."""
    try:
        service = DashboardService(db)
        stats = await service.get_stats(tenant_id)
        return DashboardStats(**stats)
    except Exception as e:
        logger.exception("Fehler in get_dashboard_stats")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/dashboard/feed", response_model=list[JourneyEventResponse])
async def get_dashboard_feed(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source_site: str | None = Query(None),
) -> list[JourneyEventResponse]:
    """Get recent events feed, optionally filtered by source_site."""
    try:
        service = EventService(db)
        events = await service.get_recent_events(
            tenant_id, limit, offset, source_site=source_site,
        )
        gaps = await service.compute_days_since_last(tenant_id, events)
        result = []
        for e in events:
            resp = JourneyEventResponse.model_validate(e)
            if e.contact:
                resp.contact_name = e.contact.name
                resp.contact_email = e.contact.email
            resp.days_since_last_visit = gaps.get(e.id)
            result.append(resp)
        return result
    except Exception as e:
        logger.exception("Fehler in get_dashboard_feed")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/dashboard/feed-by-lead", response_model=list[LeadWithEvents])
async def get_dashboard_feed_by_lead(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    events_per_lead: int = Query(10, ge=1, le=100),
    source_site: str | None = Query(None),
    category: str | None = Query(None),
    journey_status: str | None = Query(None),
    search: str | None = Query(None),
) -> list[LeadWithEvents]:
    """Feed grouped by lead, ordered by most recent event per lead."""
    try:
        service = EventService(db)
        rows = await service.get_leads_with_recent_events(
            tenant_id,
            limit,
            offset,
            events_per_lead=events_per_lead,
            source_site=source_site,
            category=category,
            journey_status=journey_status,
            search=search,
        )
        result = []
        for row in rows:
            contact = row["contact"]
            events = [JourneyEventResponse.model_validate(e) for e in row["events"]]
            result.append(
                LeadWithEvents(
                    id=contact.id,
                    name=contact.name,
                    email=contact.email,
                    phone=contact.phone,
                    source=contact.source,
                    tracking_hash=contact.tracking_hash,
                    journey_status=contact.journey_status,
                    event_count=row["event_count"],
                    last_event=row["last_event"],
                    last_event_at=row["last_event_at"],
                    created_at=contact.created_at,
                    events=events,
                )
            )
        return result
    except Exception as e:
        logger.exception("Fehler in get_dashboard_feed_by_lead")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/dashboard/sources", response_model=list[str])
async def get_dashboard_sources(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Return distinct source_site values present in this tenant's events."""
    try:
        service = EventService(db)
        return await service.get_distinct_sources(tenant_id)
    except Exception as e:
        logger.exception("Fehler in get_dashboard_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Leads (contacts with tracking) ==============


@router.get("/leads", response_model=list[LeadListResponse])
async def list_leads(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    source: str | None = Query(None),
    journey_status: str | None = Query(None),
    sort: str = Query("-created_at"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[LeadListResponse]:
    """List leads (contacts with tracking_hash)."""
    from sqlalchemy import func, or_, select

    from app.contacts.models import Contact

    try:
        query = select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.tracking_hash.isnot(None),
        )

        if search:
            term = f"%{search}%"
            query = query.where(
                or_(
                    Contact.name.ilike(term),
                    Contact.email.ilike(term),
                    Contact.phone.ilike(term),
                )
            )
        if source:
            query = query.where(Contact.source == source)
        if journey_status:
            query = query.where(Contact.journey_status == journey_status)

        # Sorting
        sort_field = sort.lstrip("-")
        sort_desc = sort.startswith("-")
        if hasattr(Contact, sort_field):
            col = getattr(Contact, sort_field)
            query = query.order_by(col.desc() if sort_desc else col)

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        contacts = list(result.scalars().all())

        # Enrich with event stats
        leads = []
        for c in contacts:
            # Get event count and last event
            ev_result = await db.execute(
                select(
                    func.count(JourneyEvent.id),
                    func.max(JourneyEvent.created_at),
                ).where(JourneyEvent.contact_id == c.id)
            )
            ev_row = ev_result.one()

            # Get last event name
            last_event_name = None
            if ev_row[1]:
                last_ev = await db.execute(
                    select(JourneyEvent.event)
                    .where(JourneyEvent.contact_id == c.id)
                    .order_by(JourneyEvent.created_at.desc())
                    .limit(1)
                )
                last_event_name = last_ev.scalar_one_or_none()

            leads.append(
                LeadListResponse(
                    id=c.id,
                    name=c.name,
                    email=c.email,
                    phone=c.phone,
                    source=c.source,
                    tracking_hash=c.tracking_hash,
                    journey_status=c.journey_status,
                    event_count=ev_row[0] or 0,
                    last_event=last_event_name,
                    last_event_at=ev_row[1],
                    created_at=c.created_at,
                )
            )

        return leads
    except Exception as e:
        logger.exception("Fehler in list_leads")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Lead Detail / Timeline ==============


@router.get("/leads/{contact_id}/timeline", response_model=list[JourneyEventResponse])
async def get_lead_timeline(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
) -> list[JourneyEventResponse]:
    """Get journey timeline for a specific lead."""
    try:
        service = EventService(db)
        events = await service.get_timeline(tenant_id, contact_id, limit)
        return [JourneyEventResponse.model_validate(e) for e in events]
    except Exception as e:
        logger.exception("Fehler in get_lead_timeline")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Ref-Codes ==============


@router.get("/refs", response_model=list[RefCodeResponse])
async def list_ref_codes(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    campaign_id: int | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[RefCodeResponse]:
    """List ref-codes."""
    try:
        service = RefCodeService(db)
        refs, _ = await service.list_refs(
            tenant_id, campaign_id, search, limit, offset
        )
        return [RefCodeResponse.model_validate(r) for r in refs]
    except Exception as e:
        logger.exception("Fehler in list_ref_codes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/refs", response_model=RefCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_ref_code(
    data: RefCodeCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RefCodeResponse:
    """Create a ref-code."""
    try:
        service = RefCodeService(db)
        ref = await service.create(tenant_id, data)
        await db.commit()
        return RefCodeResponse.model_validate(ref)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in create_ref_code")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/refs/bulk", response_model=list[RefCodeResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_ref_codes(
    data: BulkRefCodeCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[RefCodeResponse]:
    """Bulk import ref-codes."""
    try:
        service = RefCodeService(db)
        refs = await service.bulk_create(tenant_id, data)
        await db.commit()
        return [RefCodeResponse.model_validate(r) for r in refs]
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in bulk_create_ref_codes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/refs/generate")
async def generate_ref_codes(
    data: BulkGenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate N ref-codes and return as CSV download."""
    try:
        service = RefCodeService(db)
        refs = await service.bulk_generate(
            tenant_id, data.count, data.campaign_id, data.target_url, data.prefix,
            data.utm_source, data.utm_medium, data.utm_campaign,
        )
        await db.commit()

        # Build CSV
        output = io.StringIO()
        output.write("ref_code;link\n")
        for ref in refs:
            base_url = data.target_url or "https://go4.energy"
            sep = "&" if "?" in base_url else "?"
            params = [f"ref={ref.ref_code}"]
            if data.utm_source:
                params.append(f"utm_source={data.utm_source}")
            if data.utm_medium:
                params.append(f"utm_medium={data.utm_medium}")
            if data.utm_campaign:
                params.append(f"utm_campaign={data.utm_campaign}")
            link = f"{base_url}{sep}{'&'.join(params)}"
            output.write(f"{ref.ref_code};{link}\n")

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=ref-codes.csv"},
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in generate_ref_codes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/refs/{ref_id}", response_model=RefCodeResponse)
async def update_ref_code(
    ref_id: int,
    data: RefCodeUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RefCodeResponse:
    """Update a ref-code."""
    try:
        service = RefCodeService(db)
        ref = await service.update(tenant_id, ref_id, data)
        await db.commit()
        return RefCodeResponse.model_validate(ref)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in update_ref_code")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/refs/{ref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ref_code(
    ref_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a ref-code."""
    try:
        service = RefCodeService(db)
        await service.delete(tenant_id, ref_id)
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in delete_ref_code")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== CSV Import ==============


@router.get("/import/fields", response_model=list[MappableField])
async def get_mappable_fields() -> list[MappableField]:
    """Get list of fields that CSV columns can be mapped to."""
    from app.customer_journey.import_service import MAPPABLE_TARGETS

    return [MappableField(**f) for f in MAPPABLE_TARGETS]


@router.post("/import/preview", response_model=ImportPreviewResponse)
async def import_preview(
    data: ImportPreviewRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ImportPreviewResponse:
    """Preview CSV import: parse, map columns, detect conflicts."""
    try:
        from app.customer_journey.import_service import ImportService

        service = ImportService(db)
        result = await service.preview(tenant_id, data.csv_raw, data.mapping)
        return ImportPreviewResponse(**result)
    except Exception as e:
        logger.exception("Fehler in import_preview")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/import/execute")
async def import_execute(
    data: ImportExecuteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Execute CSV import: create contacts, generate ref-codes, return CSV with ref_link."""
    try:
        from app.customer_journey.import_service import ImportService

        service = ImportService(db)
        csv_output = await service.execute(
            tenant_id,
            data.csv_raw,
            data.mapping,
            data.base_url,
            data.campaign_id,
            data.conflict_resolutions,
            data.utm_source,
            data.utm_medium,
            data.utm_campaign,
        )
        await db.commit()

        csv_bytes = csv_output.encode("utf-8")
        return StreamingResponse(
            iter([csv_bytes]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=import-with-reflinks.csv"},
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in import_execute")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============== Campaigns ==============


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    campaign_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[CampaignResponse]:
    """List campaigns."""
    try:
        service = CampaignService(db)
        campaigns, _ = await service.list_campaigns(
            tenant_id, campaign_status, limit, offset
        )
        return [CampaignResponse.model_validate(c) for c in campaigns]
    except Exception as e:
        logger.exception("Fehler in list_campaigns")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    """Create a campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.create(tenant_id, data)
        await db.commit()
        return CampaignResponse.model_validate(campaign)
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in create_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CampaignResponse:
    """Update a campaign."""
    try:
        service = CampaignService(db)
        campaign = await service.update(tenant_id, campaign_id, data)
        await db.commit()
        return CampaignResponse.model_validate(campaign)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except Exception as e:
        await db.rollback()
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
        await db.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except Exception as e:
        await db.rollback()
        logger.exception("Fehler in delete_campaign")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
