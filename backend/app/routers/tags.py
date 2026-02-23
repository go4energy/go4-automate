"""Tag CRUD router — tenant-scoped tag management."""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, DuplicateError, NotFoundError
from app.models.tag import Tag
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/tags", tags=["tags"])


# --- Schemas ---


class TagCreate(BaseModel):
    """Input for creating a tag."""

    label: str = Field(..., max_length=200)
    slug: str | None = Field(None, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=50)


class TagUpdate(BaseModel):
    """Partial update for a tag."""

    label: str | None = Field(None, max_length=200)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=50)


class TagResponse(BaseModel):
    """Full response for a tag."""

    id: int
    tenant_id: str
    slug: str
    label: str
    color: str
    icon: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Helpers ---


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    slug = text.lower().strip()
    slug = re.sub(r"[äÄ]", "ae", slug)
    slug = re.sub(r"[öÖ]", "oe", slug)
    slug = re.sub(r"[üÜ]", "ue", slug)
    slug = re.sub(r"[ß]", "ss", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


# --- Endpoints ---


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    q: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[TagResponse]:
    """List all tags for the current tenant. Optional ?q= for autocomplete."""
    try:
        query = select(Tag).where(Tag.tenant_id == tenant_id)
        if q:
            query = query.where(Tag.label.ilike(f"%{q}%"))
        query = query.order_by(Tag.label.asc())
        result = await db.execute(query)
        return list(result.scalars().all())
    except Exception as e:
        logger.exception("Fehler in list_tags")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    data: TagCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    """Create a new tag."""
    try:
        slug = data.slug or _slugify(data.label)
        if not slug:
            raise HTTPException(status_code=400, detail="Slug darf nicht leer sein")

        # Check for duplicate slug
        existing = await db.execute(
            select(Tag).where(Tag.tenant_id == tenant_id, Tag.slug == slug)
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Tag", "slug")

        tag = Tag(
            tenant_id=tenant_id,
            slug=slug,
            label=data.label,
            color=data.color,
            icon=data.icon,
        )
        db.add(tag)
        await db.flush()
        await db.refresh(tag)
        logger.info(
            "Tag erstellt: {slug} (Tenant: {tenant})", slug=slug, tenant=tenant_id
        )
        return tag
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in create_tag")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    data: TagUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    """Update a tag."""
    try:
        result = await db.execute(
            select(Tag).where(Tag.id == tag_id, Tag.tenant_id == tenant_id)
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError("Tag", tag_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tag, field, value)
        await db.flush()
        await db.refresh(tag)
        logger.info(
            "Tag aktualisiert: {id} (Tenant: {tenant})", id=tag_id, tenant=tenant_id
        )
        return tag
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_tag")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tag."""
    try:
        result = await db.execute(
            select(Tag).where(Tag.id == tag_id, Tag.tenant_id == tenant_id)
        )
        tag = result.scalar_one_or_none()
        if not tag:
            raise NotFoundError("Tag", tag_id)
        await db.delete(tag)
        await db.flush()
        logger.info(
            "Tag geloescht: {id} (Tenant: {tenant})", id=tag_id, tenant=tenant_id
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_tag")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
