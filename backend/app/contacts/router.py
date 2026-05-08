"""Contacts API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.config_schema import contacts_interface
from app.contacts.schemas import (
    BulkDeleteRequest,
    BulkOperationResponse,
    BulkTagRequest,
    CompanyCreate,
    CompanyListParams,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
    ContactCreate,
    ContactListParams,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)
from app.contacts.service import CompanyService, ContactService
from app.database import get_db
from app.exceptions import AppError, DuplicateError, NotFoundError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/contacts", tags=["contacts"])

# Register standardized /config, /config/schema, /status, /metrics endpoints
contacts_interface.register_endpoints(router)


# ============== Company Endpoints ==============


@router.get("/companies", response_model=list[CompanyListResponse])
async def list_companies(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    tags: str | None = Query(None),
    owner_id: int | None = Query(None),
    industry: str | None = Query(None),
    sort: str = Query("-created_at"),
    limit: int = Query(50, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> list[CompanyListResponse]:
    """List companies for the current tenant."""
    try:
        service = CompanyService(db)
        params = CompanyListParams(
            search=search,
            tags=tags.split(",") if tags else None,
            owner_id=owner_id,
            industry=industry,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        companies, total = await service.list_companies(tenant_id, params)

        # Add contact count
        result = []
        for company in companies:
            company_dict = {
                "id": company.id,
                "tenant_id": company.tenant_id,
                "name": company.name,
                "domain": company.domain,
                "website": company.website,
                "logo_url": company.logo_url,
                "industry": company.industry,
                "size": company.size,
                "tags": company.tags,
                "contact_count": await service.get_contact_count(tenant_id, company.id),
                "created_at": company.created_at,
            }
            result.append(CompanyListResponse(**company_dict))

        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_companies")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED
)
async def create_company(
    data: CompanyCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Create a new company."""
    try:
        service = CompanyService(db)
        company = await service.create(tenant_id, data)
        return CompanyResponse(
            **{
                **company.__dict__,
                "contact_count": 0,
            }
        )
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Get a company by ID."""
    try:
        service = CompanyService(db)
        company = await service.get_by_id(tenant_id, company_id)
        contact_count = await service.get_contact_count(tenant_id, company_id)
        return CompanyResponse(
            **{
                **company.__dict__,
                "contact_count": contact_count,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CompanyResponse:
    """Update a company."""
    try:
        service = CompanyService(db)
        company = await service.update(tenant_id, company_id, data)
        contact_count = await service.get_contact_count(tenant_id, company_id)
        return CompanyResponse(
            **{
                **company.__dict__,
                "contact_count": contact_count,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a company."""
    try:
        service = CompanyService(db)
        await service.delete(tenant_id, company_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_company")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Contact Endpoints ==============


@router.get("/", response_model=list[ContactListResponse])
async def list_contacts(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None),
    company_id: int | None = Query(None),
    tags: str | None = Query(None),
    owner_id: int | None = Query(None),
    source: str | None = Query(None),
    sort: str = Query("-created_at"),
    limit: int = Query(50, ge=1, le=10000),
    offset: int = Query(0, ge=0),
) -> list[ContactListResponse]:
    """List contacts for the current tenant."""
    try:
        service = ContactService(db)
        params = ContactListParams(
            search=search,
            company_id=company_id,
            tags=tags.split(",") if tags else None,
            owner_id=owner_id,
            source=source,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        contacts, total = await service.list_contacts(tenant_id, params)

        result = []
        for contact in contacts:
            contact_dict = {
                "id": contact.id,
                "tenant_id": contact.tenant_id,
                "email": contact.email,
                "name": contact.name,
                "phone": contact.phone,
                "position": contact.position,
                "avatar_url": contact.avatar_url,
                "source": contact.source,
                "tags": contact.tags,
                "company_id": contact.company_id,
                "company_name": contact.company.name if contact.company else None,
                "owner_id": contact.owner_id,
                "created_at": contact.created_at,
            }
            result.append(ContactListResponse(**contact_dict))

        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Create a new contact."""
    try:
        service = ContactService(db)
        contact = await service.create(tenant_id, data)
        # Reload with company relationship
        contact = await service.get_by_id(tenant_id, contact.id)
        return ContactResponse(
            **{
                **contact.__dict__,
                "company_name": contact.company.name if contact.company else None,
            }
        )
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/filters")
async def get_contact_filters(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get available filter options for contacts."""
    try:
        service = ContactService(db)
        sources = await service.get_distinct_sources(tenant_id)
        tags = await service.get_distinct_tags(tenant_id)
        return {"sources": sources, "tags": tags}
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_contact_filters")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/tags/suggest")
async def suggest_tags(
    q: str = Query(default="", max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Auto-suggest distinct tags for combobox inputs.

    Used by Pipeline-Edit-UI (auto_enroll_filter) to help users pick
    consistent tag values. Substring match — case-insensitive.
    """
    try:
        service = ContactService(db)
        all_tags = await service.get_distinct_tags(tenant_id)
        if q:
            needle = q.lower()
            filtered = [t for t in all_tags if needle in t.lower()]
        else:
            filtered = list(all_tags)
        return sorted(filtered)[:limit]
    except Exception as e:
        logger.exception("Unerwarteter Fehler in suggest_tags")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Get a contact by ID."""
    try:
        service = ContactService(db)
        contact = await service.get_by_id(tenant_id, contact_id)
        # Resolve forward-source name (Forward-Audit-Badge im Frontend)
        source_name: str | None = None
        if contact.source_contact_id:
            try:
                source = await service.get_by_id(tenant_id, contact.source_contact_id)
                source_name = source.name
            except NotFoundError:
                source_name = None
        return ContactResponse(
            **{
                **contact.__dict__,
                "company_name": contact.company.name if contact.company else None,
                "source_contact_name": source_name,
            }
        )
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{contact_id}/context")
async def get_contact_context_endpoint(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregated contact context (contact + company + leadgen insights +
    LinkedIn data). Same data the engagement brain reads — exposed for the
    UI's "Insights" tab on contact and company detail pages."""
    from app.contacts.context_loader import get_contact_context

    try:
        return await get_contact_context(db, tenant_id, contact_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("get_contact_context failed for contact {cid}", cid=contact_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Update a contact."""
    try:
        service = ContactService(db)
        contact = await service.update(tenant_id, contact_id, data)
        return ContactResponse(
            **{
                **contact.__dict__,
                "company_name": contact.company.name if contact.company else None,
            }
        )
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a contact."""
    try:
        service = ContactService(db)
        await service.delete(tenant_id, contact_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_contact")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# ============== Bulk Operations ==============


@router.post("/bulk-delete", response_model=BulkOperationResponse)
async def bulk_delete_contacts(
    data: BulkDeleteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Delete multiple contacts."""
    try:
        service = ContactService(db)
        count = await service.bulk_delete(tenant_id, data.ids)
        return BulkOperationResponse(
            success=True,
            affected=count,
            message=f"{count} Kontakte gelöscht",
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_delete_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/bulk-tag", response_model=BulkOperationResponse)
async def bulk_tag_contacts(
    data: BulkTagRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Add or remove tags from multiple contacts."""
    try:
        service = ContactService(db)
        if data.action == "add":
            count = await service.bulk_add_tags(tenant_id, data.ids, data.tags)
            message = f"Tags zu {count} Kontakten hinzugefügt"
        else:
            count = await service.bulk_remove_tags(tenant_id, data.ids, data.tags)
            message = f"Tags von {count} Kontakten entfernt"

        return BulkOperationResponse(success=True, affected=count, message=message)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_tag_contacts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
