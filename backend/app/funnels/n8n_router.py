"""n8n integration router for Funnels module."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, NotFoundError, ValidationError
from app.funnels.dedup import DeduplicationService
from app.funnels.handoff_service import HandoffService
from app.funnels.schemas import (
    BulkImportResult,
    FunnelActivityCreate,
    FunnelActivityResponse,
    FunnelHandoffResponse,
    FunnelProspectCreate,
    FunnelProspectResponse,
    HandoffInitiateRequest,
    N8nActivityRequest,
    N8nBulkImportRequest,
    N8nEnrichRequest,
    N8nHandoffTriggerRequest,
    N8nImportCompany,
    N8nImportProspect,
)
from app.funnels.service import (
    ActivityService,
    CompanyService,
    ProspectService,
)
from app.utils.dependencies import get_current_tenant_id

n8n_router = APIRouter(prefix="/funnels/n8n", tags=["funnels-n8n"])


@n8n_router.post("/import-companies", response_model=BulkImportResult)
async def n8n_import_companies(
    data: N8nBulkImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkImportResult:
    """Bulk import companies from n8n workflow."""
    try:
        company_service = CompanyService(db)

        imported = 0
        skipped = 0
        duplicates = 0
        errors = []
        company_ids = []

        for item in data.items:
            if not isinstance(item, N8nImportCompany):
                skipped += 1
                continue

            try:
                # Try to find existing company by domain
                existing = None
                if item.domain:
                    existing = await company_service.find_or_create_by_domain(
                        tenant_id,
                        data.funnel_id,
                        item.name,
                        item.domain,
                    )

                if existing and data.skip_duplicates:
                    duplicates += 1
                    skipped += 1
                    company_ids.append(existing.id)
                    continue

                if existing:
                    company_ids.append(existing.id)
                    imported += 1
                else:
                    # Create new company
                    from app.funnels.schemas import FunnelCompanyCreate

                    company = await company_service.create(
                        tenant_id,
                        data.funnel_id,
                        FunnelCompanyCreate(
                            name=item.name,
                            domain=item.domain,
                            website=item.website,
                            industry=item.industry,
                            size=item.size,
                            phone=item.phone,
                            email=item.email,
                            address=item.address,
                            source=item.source,
                            source_id=item.source_id,
                            tags=item.tags,
                            custom_fields=item.custom_fields,
                        ),
                    )
                    company_ids.append(company.id)
                    imported += 1

            except Exception as e:
                errors.append(f"{item.name}: {e!s}")
                skipped += 1

        return BulkImportResult(
            total=len(data.items),
            imported=imported,
            skipped=skipped,
            duplicates=duplicates,
            errors=errors,
            prospect_ids=company_ids,  # Reusing field for company IDs
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in n8n_import_companies")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@n8n_router.post("/import-prospects", response_model=BulkImportResult)
async def n8n_import_prospects(
    data: N8nBulkImportRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkImportResult:
    """Bulk import prospects from n8n workflow."""
    try:
        prospect_service = ProspectService(db)
        company_service = CompanyService(db)
        dedup_service = DeduplicationService(db)

        imported = 0
        skipped = 0
        duplicates = 0
        errors = []
        prospect_ids = []

        for item in data.items:
            if not isinstance(item, N8nImportProspect):
                skipped += 1
                continue

            try:
                # Handle company if provided
                company_id = item.company_id
                if not company_id and (item.company_name or item.company_domain):
                    company = await company_service.find_or_create_by_domain(
                        tenant_id,
                        data.funnel_id,
                        item.company_name or item.company_domain,
                        item.company_domain,
                    )
                    if company:
                        company_id = company.id

                # Check duplicates
                if data.skip_duplicates and (item.email or item.linkedin_url):
                    check = await dedup_service.check_duplicates(
                        tenant_id,
                        email=item.email,
                        linkedin_url=item.linkedin_url,
                        phone=item.phone or item.mobile,
                    )
                    if check.has_duplicates:
                        # Check if it's in the same funnel
                        same_funnel = any(
                            m.prospect_funnel_id == data.funnel_id
                            for m in check.matches
                            if m.match_type == "funnel_prospect"
                        )
                        if same_funnel:
                            duplicates += 1
                            skipped += 1
                            continue

                # Create prospect
                prospect = await prospect_service.create(
                    tenant_id,
                    data.funnel_id,
                    FunnelProspectCreate(
                        name=item.name,
                        email=item.email,
                        first_name=item.first_name,
                        last_name=item.last_name,
                        phone=item.phone,
                        mobile=item.mobile,
                        position=item.position,
                        department=item.department,
                        seniority=item.seniority,
                        linkedin_url=item.linkedin_url,
                        twitter_url=item.twitter_url,
                        company_id=company_id,
                        stage_id=item.stage_id,
                        source=item.source,
                        source_id=item.source_id,
                        score=item.score,
                        tags=item.tags,
                        custom_fields=item.custom_fields,
                    ),
                    check_duplicates=not data.skip_duplicates,
                )
                prospect_ids.append(prospect.id)
                imported += 1

            except Exception as e:
                errors.append(f"{item.name}: {e!s}")
                skipped += 1

        return BulkImportResult(
            total=len(data.items),
            imported=imported,
            skipped=skipped,
            duplicates=duplicates,
            errors=errors,
            prospect_ids=prospect_ids,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in n8n_import_prospects")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@n8n_router.post("/enrich", response_model=FunnelProspectResponse)
async def n8n_enrich_prospect(
    data: N8nEnrichRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelProspectResponse:
    """Submit enrichment data for a prospect from n8n workflow."""
    try:
        service = ProspectService(db)
        prospect = await service.get_by_id(tenant_id, data.prospect_id)

        # Merge enrichment data
        current_enrichment = prospect.enrichment_data or {}
        merged_enrichment = {**current_enrichment, **data.enrichment_data}

        # Build update data
        from app.funnels.schemas import FunnelProspectUpdate

        update_data = FunnelProspectUpdate(enrichment_data=merged_enrichment)

        # Optionally update fields from enrichment
        if data.update_fields:
            enrichment = data.enrichment_data

            # Map common enrichment fields
            if enrichment.get("email") and not prospect.email:
                update_data.email = enrichment["email"]
            if enrichment.get("phone") and not prospect.phone:
                update_data.phone = enrichment["phone"]
            if enrichment.get("linkedin_url") and not prospect.linkedin_url:
                update_data.linkedin_url = enrichment["linkedin_url"]
            if enrichment.get("position") and not prospect.position:
                update_data.position = enrichment["position"]
            if enrichment.get("department") and not prospect.department:
                update_data.department = enrichment["department"]
            if enrichment.get("seniority") and not prospect.seniority:
                update_data.seniority = enrichment["seniority"]

            # Update email verification if provided
            if enrichment.get("email_verified"):
                update_data.email_verified = True

        prospect = await service.update(tenant_id, data.prospect_id, update_data)

        # Log enrichment activity
        activity_service = ActivityService(db)
        await activity_service.create(
            tenant_id,
            data.prospect_id,
            FunnelActivityCreate(
                activity_type="enrichment_completed",
                subject="Anreicherung abgeschlossen",
                metadata={"source": data.enrichment_data.get("source", "n8n")},
            ),
        )

        return FunnelProspectResponse(
            **{
                **prospect.__dict__,
                "company_name": prospect.company.name if prospect.company else None,
                "stage_name": prospect.stage.name if prospect.stage else None,
                "owner_name": prospect.owner.display_name if prospect.owner else None,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in n8n_enrich_prospect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@n8n_router.post("/log-activity", response_model=FunnelActivityResponse)
async def n8n_log_activity(
    data: N8nActivityRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelActivityResponse:
    """Log an outreach activity from n8n workflow."""
    try:
        service = ActivityService(db)
        activity = await service.create(
            tenant_id,
            data.prospect_id,
            FunnelActivityCreate(
                activity_type=data.activity_type,
                subject=data.subject,
                content=data.content,
                channel=data.channel,
                external_id=data.external_id,
                external_url=data.external_url,
                activity_date=data.activity_date or datetime.utcnow(),
                metadata=data.metadata,
            ),
        )
        return FunnelActivityResponse(
            **{
                **activity.__dict__,
                "metadata": activity.metadata_,
                "user_name": None,
            }
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in n8n_log_activity")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@n8n_router.post("/trigger-handoff", response_model=FunnelHandoffResponse)
async def n8n_trigger_handoff(
    data: N8nHandoffTriggerRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FunnelHandoffResponse:
    """Trigger a handoff from n8n workflow."""
    try:
        service = HandoffService(db)
        handoff = await service.initiate_handoff(
            tenant_id,
            data.prospect_id,
            HandoffInitiateRequest(
                create_deal=data.create_deal,
                deal_title=data.deal_title,
                deal_value=data.deal_value,
            ),
            triggered_by="n8n",
        )
        return FunnelHandoffResponse(
            **{
                **handoff.__dict__,
                "prospect_name": handoff.prospect.name if handoff.prospect else None,
                "company_name": handoff.company.name if handoff.company else None,
            }
        )
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in n8n_trigger_handoff")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
