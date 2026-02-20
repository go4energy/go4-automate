"""Creator service - CRUD and business logic for content pieces and calendar."""

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.creator.models import CreatorCalendar, CreatorPiece
from app.creator.schemas import (
    CreatorApprove,
    CreatorCalendarCreate,
    CreatorGenerate,
    CreatorGenerateFromTopic,
    CreatorPieceCreate,
    CreatorPieceUpdate,
)
from app.exceptions import ExternalServiceError, NotFoundError, ValidationError
from app.services.llm import LLMService
from app.services.meta import MetaService

CONTENT_PROMPT_TEMPLATE = """Erstelle einen Social-Media-Post fuer {platform} zum Thema "{topic}".
Unternehmen: {company} | Tonalitaet: {tone} | Zielgruppe: {audience}
Content-Typ: {content_type} | Funnel-Stage: {funnel_stage}

Regeln:
- Max 2200 Zeichen fuer die Caption
- Hook am Anfang (erster Satz muss Aufmerksamkeit erregen)
- CTA am Ende (klare Handlungsaufforderung)
- 5-8 relevante Hashtags
- Kurze Version (max 280 Zeichen) fuer Twitter/X

{additional_instructions}

Antworte als JSON: {{"title": "...", "caption": "...", "short": "...", "hashtags": "...", "hook": "...", "cta": "..."}}"""


class CreatorService:
    """Service for content piece and calendar management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_piece(
        self, tenant_id: str, data: CreatorPieceCreate
    ) -> CreatorPiece:
        """Create a new content piece."""
        piece = CreatorPiece(
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
        due: bool = False,
        published_last_days: int | None = None,
    ) -> list[CreatorPiece]:
        """List content pieces for a tenant with optional filters."""
        query = select(CreatorPiece).where(CreatorPiece.tenant_id == tenant_id)
        if status:
            query = query.where(CreatorPiece.status == status)
        if platform:
            query = query.where(CreatorPiece.platform == platform)
        if due:
            now = datetime.utcnow()
            query = query.where(
                CreatorPiece.scheduled_at <= now,
                CreatorPiece.status == "scheduled",
            )
        if published_last_days is not None:
            cutoff = datetime.utcnow() - timedelta(days=published_last_days)
            query = query.where(
                CreatorPiece.posted_at >= cutoff,
                CreatorPiece.status == "published",
            )
        query = query.order_by(CreatorPiece.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_piece_by_id(self, tenant_id: str, piece_id: int) -> CreatorPiece:
        """Get a single content piece by ID (scoped to tenant)."""
        result = await self.db.execute(
            select(CreatorPiece).where(
                CreatorPiece.id == piece_id,
                CreatorPiece.tenant_id == tenant_id,
            )
        )
        piece = result.scalar_one_or_none()
        if not piece:
            raise NotFoundError("CreatorPiece", piece_id)
        return piece

    async def update_piece(
        self, tenant_id: str, piece_id: int, data: CreatorPieceUpdate
    ) -> CreatorPiece:
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
            "Content geloescht: {id} (Tenant: {tenant})",
            id=piece_id,
            tenant=tenant_id,
        )

    async def generate_content(
        self,
        tenant_id: str,
        data: CreatorGenerate,
        tenant_config: dict,
    ) -> CreatorPiece:
        """Generate content via LLM and save as draft."""
        result, model_id = await self._generate_via_registry_or_legacy(
            tenant_id, data, tenant_config
        )

        piece = CreatorPiece(
            tenant_id=tenant_id,
            title=result.get("title", data.topic),
            topic=data.topic,
            content_type=data.content_type,
            platform=data.platform,
            caption=result.get("caption", ""),
            short=result.get("short", ""),
            hashtags=result.get("hashtags", ""),
            hook=result.get("hook", ""),
            cta=result.get("cta", ""),
            status="draft",
            funnel_stage=data.funnel_stage,
            buyer_persona=data.buyer_persona,
            created_by="ai",
            ai_model=model_id,
        )
        self.db.add(piece)
        await self.db.flush()
        await self.db.refresh(piece)
        logger.info(
            "Content generiert: {title} (Tenant: {tenant})",
            title=piece.title,
            tenant=tenant_id,
        )
        await self._log_activity(
            tenant_id,
            "creator.generated",
            f"Post '{piece.title}' generiert",
            entity_type="creator_piece",
            entity_id=piece.id,
            severity="success",
        )
        return piece

    async def generate_from_topic(
        self,
        tenant_id: str,
        data: CreatorGenerateFromTopic,
        tenant_config: dict,
    ) -> CreatorPiece:
        """Generate content from a topic (decoupled from Collector)."""
        generate_data = CreatorGenerate(
            topic=data.title,
            platform=data.platform,
            content_type=data.content_type,
            additional_instructions=data.description,
        )
        piece = await self.generate_content(tenant_id, generate_data, tenant_config)

        if data.image_url and piece.media_urls is None:
            piece.media_urls = [data.image_url]
        elif data.image_url:
            piece.media_urls = [data.image_url] + (piece.media_urls or [])

        await self.db.flush()
        await self.db.refresh(piece)
        return piece

    async def approve_content(
        self, tenant_id: str, piece_id: int, data: CreatorApprove
    ) -> CreatorPiece:
        """Approve a draft content piece and schedule it."""
        piece = await self.get_piece_by_id(tenant_id, piece_id)
        if piece.status != "draft":
            raise ValidationError(
                f"Nur Drafts koennen genehmigt werden (aktuell: {piece.status})"
            )
        piece.status = "scheduled"
        piece.approved_by = data.approved_by
        piece.approved_at = datetime.utcnow()
        piece.scheduled_at = data.scheduled_at
        await self.db.flush()
        await self.db.refresh(piece)
        logger.info(
            "Content genehmigt: {id} von {by} (Tenant: {tenant})",
            id=piece_id,
            by=data.approved_by,
            tenant=tenant_id,
        )
        await self._log_activity(
            tenant_id,
            "creator.approved",
            f"Post '{piece.title}' genehmigt",
            entity_type="creator_piece",
            entity_id=piece.id,
            severity="success",
        )
        return piece

    async def publish_content(self, tenant_id: str, piece_id: int) -> CreatorPiece:
        """Publish a scheduled content piece via Meta API."""
        piece = await self.get_piece_by_id(tenant_id, piece_id)
        if piece.status != "scheduled":
            raise ValidationError(
                f"Nur geplante Inhalte koennen veroeffentlicht werden (aktuell: {piece.status})"
            )

        meta = MetaService()
        caption = piece.caption or ""
        if piece.hashtags:
            caption = f"{caption}\n\n{piece.hashtags}"

        try:
            if piece.platform == "instagram":
                image_url = (piece.media_urls or [""])[0] if piece.media_urls else ""
                if not image_url:
                    raise ValidationError("Instagram Posts benoetigen ein Bild")
                post_id = await meta.post_to_instagram(caption, image_url)
            else:
                post_id = await meta.post_to_facebook(caption)

            piece.status = "published"
            piece.meta_post_id = post_id
            piece.posted_at = datetime.utcnow()
            piece.error_message = None
        except ExternalServiceError as e:
            piece.status = "failed"
            piece.error_message = e.message
            logger.error(
                "Publishing fehlgeschlagen: {id} - {err}",
                id=piece_id,
                err=e.message,
            )

        await self.db.flush()
        await self.db.refresh(piece)
        if piece.status == "published":
            await self._log_activity(
                tenant_id,
                "creator.published",
                f"Post '{piece.title}' veroeffentlicht",
                entity_type="creator_piece",
                entity_id=piece.id,
                severity="success",
            )
        elif piece.status == "failed":
            await self._log_activity(
                tenant_id,
                "creator.failed",
                f"Post '{piece.title}' fehlgeschlagen",
                detail=piece.error_message,
                entity_type="creator_piece",
                entity_id=piece.id,
                severity="error",
            )
        return piece

    async def _log_activity(
        self,
        tenant_id: str,
        action: str,
        title: str,
        detail: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        severity: str = "info",
    ) -> None:
        """Log an activity event."""
        from app.services.activity import ActivityService

        await ActivityService(self.db).log(
            tenant_id,
            "creator",
            action,
            title,
            detail=detail,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
        )

    async def get_next_topic(self, tenant_id: str, topics: list[str]) -> dict:
        """Round-robin: return the next topic based on the last used topic."""
        if not topics:
            raise ValidationError("Keine Themen angegeben")

        result = await self.db.execute(
            select(CreatorPiece.topic)
            .where(
                CreatorPiece.tenant_id == tenant_id,
                CreatorPiece.topic.in_(topics),
            )
            .order_by(CreatorPiece.created_at.desc())
            .limit(1)
        )
        last_topic = result.scalar_one_or_none()

        if last_topic and last_topic in topics:
            last_idx = topics.index(last_topic)
            next_idx = (last_idx + 1) % len(topics)
        else:
            next_idx = 0

        return {
            "next_topic": topics[next_idx],
            "topics": topics,
            "last_used_index": next_idx,
        }

    async def update_engagement(self, tenant_id: str, piece_id: int) -> CreatorPiece:
        """Fetch engagement metrics from Meta API and update the piece."""
        piece = await self.get_piece_by_id(tenant_id, piece_id)
        if not piece.meta_post_id:
            raise ValidationError("Kein Meta Post ID vorhanden")

        meta = MetaService()
        metrics = await meta.get_post_engagement(piece.meta_post_id)

        piece.reach = metrics.get("reach", piece.reach)
        piece.impressions = metrics.get("impressions", piece.impressions)
        piece.engagement = metrics.get("engagement", piece.engagement)
        if piece.reach > 0:
            piece.engagement_rate = round(piece.engagement / piece.reach * 100, 2)

        await self.db.flush()
        await self.db.refresh(piece)
        logger.info(
            "Engagement aktualisiert: {id} (Reach: {reach})",
            id=piece_id,
            reach=piece.reach,
        )
        return piece

    async def create_calendar_entry(
        self, tenant_id: str, data: CreatorCalendarCreate
    ) -> CreatorCalendar:
        """Create a calendar entry for a content piece."""
        await self.get_piece_by_id(tenant_id, data.content_id)
        entry = CreatorCalendar(
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
            "Calendar-Eintrag erstellt fuer Content {id} (Tenant: {tenant})",
            id=data.content_id,
            tenant=tenant_id,
        )
        return entry

    async def list_calendar(self, tenant_id: str) -> list[CreatorCalendar]:
        """List calendar entries for a tenant."""
        query = (
            select(CreatorCalendar)
            .where(CreatorCalendar.tenant_id == tenant_id)
            .order_by(CreatorCalendar.scheduled_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _generate_via_registry_or_legacy(
        self,
        tenant_id: str,
        data: CreatorGenerate,
        tenant_config: dict,
    ) -> tuple[dict, str]:
        """Try prompt registry first, fallback to legacy template."""
        from app.exceptions import NotFoundError as _NotFoundError
        from app.schemas.prompt import PromptExecuteRequest
        from app.services.prompt import PromptService

        try:
            prompt_service = PromptService(self.db)
            variables = {
                "platform": data.platform,
                "topic": data.topic,
                "content_type": data.content_type,
                "funnel_stage": data.funnel_stage or "awareness",
                "additional_instructions": data.additional_instructions or "",
            }
            exec_result = await prompt_service.execute(
                tenant_id,
                PromptExecuteRequest(
                    prompt_slug="social-media-post", variables=variables
                ),
                tenant_config,
            )
            result = exec_result["result"]
            if isinstance(result, str):
                import json

                result = json.loads(result)
            model_id = exec_result["model"]
            logger.info("Content via Prompt Registry generiert")
            return result, model_id
        except _NotFoundError:
            logger.info(
                "Prompt 'social-media-post' nicht gefunden, nutze Legacy-Template"
            )
            return await self._generate_legacy(data, tenant_config)

    async def _generate_legacy(
        self,
        data: CreatorGenerate,
        tenant_config: dict,
    ) -> tuple[dict, str]:
        """Generate content using the legacy hardcoded template."""
        company = tenant_config.get("COMPANY_NAME", "")
        tone = tenant_config.get("CONTENT_TONE", "professional")
        audience = tenant_config.get("TARGET_AUDIENCE", "B2B Entscheider")

        prompt = CONTENT_PROMPT_TEMPLATE.format(
            platform=data.platform,
            topic=data.topic,
            company=company,
            tone=tone,
            audience=audience,
            content_type=data.content_type,
            funnel_stage=data.funnel_stage or "awareness",
            additional_instructions=data.additional_instructions or "",
        )

        llm = LLMService(tenant_config=tenant_config)
        result = await llm.generate_json("content", prompt)
        _, model_id = _get_content_model()
        return result, model_id


def _get_content_model() -> tuple[str, str]:
    """Return provider and model for content task."""
    from app.services.llm import _get_model_for_task

    return _get_model_for_task("content")
