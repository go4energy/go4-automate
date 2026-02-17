"""Content service - CRUD and business logic for content pieces and calendar."""

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.content_calendar import ContentCalendar
from app.models.content_piece import ContentPiece
from app.schemas.content import (
    ContentCalendarCreate,
    ContentPieceCreate,
    ContentPieceUpdate,
)


class ContentService:
    """Service for content piece and calendar management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_piece(
        self, tenant_id: str, data: ContentPieceCreate
    ) -> ContentPiece:
        """Create a new content piece."""
        piece = ContentPiece(
            tenant_id=tenant_id,
            title=data.title,
            topic=data.topic,
            content_type=data.content_type,
            platform=data.platform,
            caption=data.caption,
            short=data.short,
            hashtags=data.hashtags,
            hook=data.hook,
            cta=data.cta,
            media_urls=data.media_urls,
            status=data.status,
            scheduled_at=data.scheduled_at,
            funnel_stage=data.funnel_stage,
            buyer_persona=data.buyer_persona,
            created_by=data.created_by,
            ai_model=data.ai_model,
        )
        self.db.add(piece)
        await self.db.flush()
        await self.db.refresh(piece)
        logger.info(
            "Content erstellt: {title} (Tenant: {tenant})",
            title=data.title,
            tenant=tenant_id,
        )
        return piece

    async def list_pieces(
        self,
        tenant_id: str,
        status: str | None = None,
        platform: str | None = None,
    ) -> list[ContentPiece]:
        """List content pieces for a tenant with optional filters."""
        query = select(ContentPiece).where(ContentPiece.tenant_id == tenant_id)
        if status:
            query = query.where(ContentPiece.status == status)
        if platform:
            query = query.where(ContentPiece.platform == platform)
        query = query.order_by(ContentPiece.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_piece_by_id(self, tenant_id: str, piece_id: int) -> ContentPiece:
        """Get a single content piece by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(ContentPiece).where(
                ContentPiece.id == piece_id,
                ContentPiece.tenant_id == tenant_id,
            )
        )
        piece = result.scalar_one_or_none()
        if not piece:
            raise NotFoundError("ContentPiece", piece_id)
        return piece

    async def update_piece(
        self, tenant_id: str, piece_id: int, data: ContentPieceUpdate
    ) -> ContentPiece:
        """Update a content piece."""
        piece = await self.get_piece_by_id(tenant_id, piece_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(piece, field, value)
        await self.db.flush()
        await self.db.refresh(piece)
        logger.info(
            "Content aktualisiert: {id} (Tenant: {tenant})",
            id=piece_id,
            tenant=tenant_id,
        )
        return piece

    async def delete_piece(self, tenant_id: str, piece_id: int) -> None:
        """Delete a content piece."""
        piece = await self.get_piece_by_id(tenant_id, piece_id)
        await self.db.delete(piece)
        await self.db.flush()
        logger.info(
            "Content gelöscht: {id} (Tenant: {tenant})",
            id=piece_id,
            tenant=tenant_id,
        )

    async def create_calendar_entry(
        self, tenant_id: str, data: ContentCalendarCreate
    ) -> ContentCalendar:
        """Create a calendar entry for a content piece."""
        await self.get_piece_by_id(tenant_id, data.content_id)
        entry = ContentCalendar(
            tenant_id=tenant_id,
            content_id=data.content_id,
            platform=data.platform,
            scheduled_at=data.scheduled_at,
            time_slot=data.time_slot,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        logger.info(
            "Calendar-Eintrag erstellt für Content {id} (Tenant: {tenant})",
            id=data.content_id,
            tenant=tenant_id,
        )
        return entry

    async def list_calendar(self, tenant_id: str) -> list[ContentCalendar]:
        """List calendar entries for a tenant."""
        query = (
            select(ContentCalendar)
            .where(ContentCalendar.tenant_id == tenant_id)
            .order_by(ContentCalendar.scheduled_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
