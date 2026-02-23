"""Stream CRUD router — tenant-scoped stream management."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, DuplicateError, NotFoundError
from app.models.stream import Stream
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/streams", tags=["streams"])


# --- Schemas ---


class StreamCreate(BaseModel):
    """Input for creating a stream."""

    label: str = Field(..., max_length=200)
    slug: str | None = Field(None, max_length=100)
    description: str | None = None
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=50)


class StreamUpdate(BaseModel):
    """Partial update for a stream."""

    label: str | None = Field(None, max_length=200)
    description: str | None = None
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(None, max_length=50)
    active: bool | None = None


class StreamResponse(BaseModel):
    """Full response for a stream."""

    id: int
    tenant_id: str
    slug: str
    label: str
    description: str | None = None
    color: str
    icon: str | None = None
    active: bool

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


@router.get("/", response_model=list[StreamResponse])
async def list_streams(
    q: str | None = Query(None, max_length=200),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[StreamResponse]:
    """List all streams for the current tenant. Optional ?q= for autocomplete."""
    try:
        query = select(Stream).where(Stream.tenant_id == tenant_id)
        if q:
            query = query.where(Stream.label.ilike(f"%{q}%"))
        query = query.order_by(Stream.label.asc())
        result = await db.execute(query)
        return list(result.scalars().all())
    except Exception as e:
        logger.exception("Fehler in list_streams")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stream(
    data: StreamCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StreamResponse:
    """Create a new stream."""
    try:
        slug = data.slug or _slugify(data.label)
        if not slug:
            raise HTTPException(status_code=400, detail="Slug darf nicht leer sein")

        # Check for duplicate slug
        existing = await db.execute(
            select(Stream).where(Stream.tenant_id == tenant_id, Stream.slug == slug)
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Stream", "slug")

        stream = Stream(
            tenant_id=tenant_id,
            slug=slug,
            label=data.label,
            description=data.description,
            color=data.color,
            icon=data.icon,
        )
        db.add(stream)
        await db.flush()
        await db.refresh(stream)
        logger.info(
            "Stream erstellt: {slug} (Tenant: {tenant})", slug=slug, tenant=tenant_id
        )
        return stream
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Fehler in create_stream")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/{stream_id}", response_model=StreamResponse)
async def update_stream(
    stream_id: int,
    data: StreamUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> StreamResponse:
    """Update a stream."""
    try:
        result = await db.execute(
            select(Stream).where(Stream.id == stream_id, Stream.tenant_id == tenant_id)
        )
        stream = result.scalar_one_or_none()
        if not stream:
            raise NotFoundError("Stream", stream_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stream, field, value)
        await db.flush()
        await db.refresh(stream)
        logger.info(
            "Stream aktualisiert: {id} (Tenant: {tenant})",
            id=stream_id,
            tenant=tenant_id,
        )
        return stream
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in update_stream")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stream(
    stream_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a stream."""
    try:
        result = await db.execute(
            select(Stream).where(Stream.id == stream_id, Stream.tenant_id == tenant_id)
        )
        stream = result.scalar_one_or_none()
        if not stream:
            raise NotFoundError("Stream", stream_id)
        await db.delete(stream)
        await db.flush()
        logger.info(
            "Stream geloescht: {id} (Tenant: {tenant})",
            id=stream_id,
            tenant=tenant_id,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Fehler in delete_stream")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
