"""Contacts service - CRUD and business logic for contacts and companies."""

from loguru import logger
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Company, Contact
from app.contacts.schemas import (
    CompanyCreate,
    CompanyListParams,
    CompanyUpdate,
    ContactCreate,
    ContactListParams,
    ContactUpdate,
)
from app.exceptions import DuplicateError, NotFoundError


class CompanyService:
    """Service for company management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: CompanyCreate) -> Company:
        """Create a new company."""
        company = Company(
            tenant_id=tenant_id,
            name=data.name,
            domain=data.domain,
            website=data.website,
            logo_url=data.logo_url,
            industry=data.industry,
            size=data.size,
            annual_revenue=data.annual_revenue,
            address=data.address,
            phone=data.phone,
            email=data.email,
            tags=data.tags,
            custom_fields=data.custom_fields,
            description=data.description,
            owner_id=data.owner_id,
        )
        self.db.add(company)
        await self.db.flush()
        await self.db.refresh(company)
        logger.info(
            "Company erstellt: {name} (Tenant: {tenant})",
            name=data.name,
            tenant=tenant_id,
        )
        return company

    async def get_by_id(self, tenant_id: str, company_id: int) -> Company:
        """Get a company by ID."""
        result = await self.db.execute(
            select(Company)
            .options(selectinload(Company.contacts))
            .where(Company.id == company_id, Company.tenant_id == tenant_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise NotFoundError("Company", company_id)
        return company

    async def list_companies(
        self, tenant_id: str, params: CompanyListParams
    ) -> tuple[list[Company], int]:
        """List companies with filters and pagination."""
        query = select(Company).where(Company.tenant_id == tenant_id)

        # Search
        if params.search:
            search_term = f"%{params.search}%"
            query = query.where(
                or_(
                    Company.name.ilike(search_term),
                    Company.domain.ilike(search_term),
                    Company.email.ilike(search_term),
                )
            )

        # Filters
        if params.tags:
            query = query.where(Company.tags.op("?|")(params.tags))
        if params.owner_id:
            query = query.where(Company.owner_id == params.owner_id)
        if params.industry:
            query = query.where(Company.industry == params.industry)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Sorting
        sort_field = params.sort.lstrip("-")
        sort_desc = params.sort.startswith("-")
        if hasattr(Company, sort_field):
            order_col = getattr(Company, sort_field)
            query = query.order_by(order_col.desc() if sort_desc else order_col)

        # Pagination
        query = query.offset(params.offset).limit(params.limit)

        result = await self.db.execute(query)
        companies = list(result.scalars().all())

        return companies, total

    async def update(
        self, tenant_id: str, company_id: int, data: CompanyUpdate
    ) -> Company:
        """Update a company."""
        company = await self.get_by_id(tenant_id, company_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)

        await self.db.flush()
        await self.db.refresh(company)
        logger.info("Company aktualisiert: {id}", id=company_id)
        return company

    async def delete(self, tenant_id: str, company_id: int) -> None:
        """Delete a company."""
        company = await self.get_by_id(tenant_id, company_id)
        await self.db.delete(company)
        await self.db.flush()
        logger.info("Company gelöscht: {id}", id=company_id)

    async def get_contact_count(self, tenant_id: str, company_id: int) -> int:
        """Get the number of contacts for a company."""
        result = await self.db.execute(
            select(func.count(Contact.id)).where(
                Contact.tenant_id == tenant_id, Contact.company_id == company_id
            )
        )
        return result.scalar() or 0


class ContactService:
    """Service for contact management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, tenant_id: str, data: ContactCreate) -> Contact:
        """Create a new contact."""
        # Check for duplicate email
        existing = await self.db.execute(
            select(Contact).where(
                Contact.tenant_id == tenant_id, Contact.email == data.email
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Contact", "email")

        contact = Contact(
            tenant_id=tenant_id,
            email=data.email,
            name=data.name,
            phone=data.phone,
            mobile=data.mobile,
            position=data.position,
            avatar_url=data.avatar_url,
            source=data.source,
            tags=data.tags,
            custom_fields=data.custom_fields,
            linkedin=data.linkedin,
            twitter=data.twitter,
            notes=data.notes,
            company_id=data.company_id,
            owner_id=data.owner_id,
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Contact erstellt: {email} (Tenant: {tenant})",
            email=data.email,
            tenant=tenant_id,
        )
        return contact

    async def get_by_id(self, tenant_id: str, contact_id: int) -> Contact:
        """Get a contact by ID."""
        result = await self.db.execute(
            select(Contact)
            .options(selectinload(Contact.company))
            .where(Contact.id == contact_id, Contact.tenant_id == tenant_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFoundError("Contact", contact_id)
        return contact

    async def list_contacts(
        self, tenant_id: str, params: ContactListParams
    ) -> tuple[list[Contact], int]:
        """List contacts with filters and pagination."""
        query = (
            select(Contact)
            .options(selectinload(Contact.company))
            .where(Contact.tenant_id == tenant_id)
        )

        # Search
        if params.search:
            search_term = f"%{params.search}%"
            query = query.where(
                or_(
                    Contact.name.ilike(search_term),
                    Contact.email.ilike(search_term),
                    Contact.phone.ilike(search_term),
                )
            )

        # Filters
        if params.company_id:
            query = query.where(Contact.company_id == params.company_id)
        if params.tags:
            query = query.where(Contact.tags.op("?|")(params.tags))
        if params.owner_id:
            query = query.where(Contact.owner_id == params.owner_id)
        if params.source:
            query = query.where(Contact.source == params.source)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Sorting
        sort_field = params.sort.lstrip("-")
        sort_desc = params.sort.startswith("-")
        if hasattr(Contact, sort_field):
            order_col = getattr(Contact, sort_field)
            query = query.order_by(order_col.desc() if sort_desc else order_col)

        # Pagination
        query = query.offset(params.offset).limit(params.limit)

        result = await self.db.execute(query)
        contacts = list(result.scalars().all())

        return contacts, total

    async def update(
        self, tenant_id: str, contact_id: int, data: ContactUpdate
    ) -> Contact:
        """Update a contact."""
        contact = await self.get_by_id(tenant_id, contact_id)

        # Check for email uniqueness if changing email
        if data.email and data.email != contact.email:
            existing = await self.db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.email == data.email,
                    Contact.id != contact_id,
                )
            )
            if existing.scalar_one_or_none():
                raise DuplicateError("Contact", "email")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(contact, key, value)

        await self.db.flush()
        await self.db.refresh(contact)
        logger.info("Contact aktualisiert: {id}", id=contact_id)
        return contact

    async def delete(self, tenant_id: str, contact_id: int) -> None:
        """Delete a contact."""
        contact = await self.get_by_id(tenant_id, contact_id)
        await self.db.delete(contact)
        await self.db.flush()
        logger.info("Contact gelöscht: {id}", id=contact_id)

    async def bulk_delete(self, tenant_id: str, ids: list[int]) -> int:
        """Delete multiple contacts."""
        result = await self.db.execute(
            delete(Contact).where(Contact.tenant_id == tenant_id, Contact.id.in_(ids))
        )
        await self.db.flush()
        logger.info("Contacts gelöscht: {count}", count=result.rowcount)
        return result.rowcount

    async def bulk_add_tags(
        self, tenant_id: str, ids: list[int], tags: list[str]
    ) -> int:
        """Add tags to multiple contacts."""
        # Get contacts
        result = await self.db.execute(
            select(Contact).where(Contact.tenant_id == tenant_id, Contact.id.in_(ids))
        )
        contacts = list(result.scalars().all())

        for contact in contacts:
            current_tags = set(contact.tags or [])
            current_tags.update(tags)
            contact.tags = list(current_tags)

        await self.db.flush()
        logger.info("Tags hinzugefügt zu {count} Contacts", count=len(contacts))
        return len(contacts)

    async def bulk_remove_tags(
        self, tenant_id: str, ids: list[int], tags: list[str]
    ) -> int:
        """Remove tags from multiple contacts."""
        result = await self.db.execute(
            select(Contact).where(Contact.tenant_id == tenant_id, Contact.id.in_(ids))
        )
        contacts = list(result.scalars().all())

        for contact in contacts:
            current_tags = set(contact.tags or [])
            current_tags.difference_update(tags)
            contact.tags = list(current_tags)

        await self.db.flush()
        logger.info("Tags entfernt von {count} Contacts", count=len(contacts))
        return len(contacts)

    async def get_distinct_sources(self, tenant_id: str) -> list[str]:
        """Get distinct sources for filter dropdown."""
        result = await self.db.execute(
            select(Contact.source)
            .where(Contact.tenant_id == tenant_id, Contact.source.isnot(None))
            .distinct()
        )
        return [row[0] for row in result.all() if row[0]]

    async def get_distinct_tags(self, tenant_id: str) -> list[str]:
        """Get distinct tags for filter dropdown."""
        # Use jsonb_array_elements_text for JSONB arrays
        result = await self.db.execute(
            select(
                func.jsonb_array_elements_text(Contact.tags).label("tag")
            )
            .where(Contact.tenant_id == tenant_id, Contact.tags.isnot(None))
            .distinct()
        )
        return [row[0] for row in result.all()]
