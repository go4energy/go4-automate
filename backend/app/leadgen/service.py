"""Leadgen services - Campaign, Run, Place management."""

from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Company, Contact
from app.engagement.models import EngagementPipeline
from app.engagement.schemas import (
    BulkEnrollRequest,
)
from app.engagement.schemas import (
    PipelineCreate as EngagementPipelineCreate,
)
from app.engagement.service import (
    EnrollmentService as EngagementEnrollmentService,
)
from app.engagement.service import (
    PipelineService as EngagementPipelineService,
)
from app.exceptions import DuplicateError, NotFoundError, ValidationError
from app.leadgen.models import (
    LeadgenCampaign,
    LeadgenImpressum,
    LeadgenLLMInsights,
    LeadgenPlace,
    LeadgenRun,
)
from app.leadgen.schemas import (
    CampaignCreate,
    CampaignStats,
    CampaignUpdate,
)


class CampaignService:
    """CRUD + Pipeline-Handoff for leadgen campaigns."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, tenant_id: str, data: CampaignCreate
    ) -> LeadgenCampaign:
        """Create campaign; optionally auto-create the linked engagement pipeline."""
        existing = await self.db.execute(
            select(LeadgenCampaign).where(
                LeadgenCampaign.tenant_id == tenant_id,
                LeadgenCampaign.slug == data.slug,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Leadgen-Kampagne", "slug")

        pipeline_id = data.target_engagement_pipeline_id

        if pipeline_id is None and data.create_new_pipeline:
            pipeline = await self._auto_create_pipeline(tenant_id, data)
            pipeline_id = pipeline.id
        elif pipeline_id is not None:
            await self._assert_pipeline_exists(tenant_id, pipeline_id)

        campaign = LeadgenCampaign(
            tenant_id=tenant_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            queries=data.queries,
            language=data.language,
            region=data.region,
            target_match_threshold=data.target_match_threshold,
            target_engagement_pipeline_id=pipeline_id,
            source=data.source,
            source_config=data.source_config,
            status="draft",
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def _auto_create_pipeline(
        self, tenant_id: str, data: CampaignCreate
    ) -> EngagementPipeline:
        """Create a default Engagement pipeline for this leadgen campaign."""
        svc = EngagementPipelineService(self.db)
        base_slug = f"leadgen-{data.slug}"
        slug = base_slug
        suffix = 1
        while True:
            existing = await self.db.execute(
                select(EngagementPipeline).where(
                    EngagementPipeline.tenant_id == tenant_id,
                    EngagementPipeline.slug == slug,
                )
            )
            if existing.scalar_one_or_none() is None:
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"
            if suffix > 100:
                raise ValidationError(
                    "Konnte keinen freien Slug fuer Auto-Pipeline finden"
                )

        pipeline = await svc.create(
            tenant_id,
            EngagementPipelineCreate(
                name=f"Leadgen: {data.name}",
                slug=slug,
                product_name=data.name,
                target_audience=data.description or "",
                channels=["postmail", "email"],
                goal="erstkontakt",
                tone_of_voice="professionell",
                min_days_between_touches=3,
                is_active=True,
            ),
        )
        await self.db.flush()
        return pipeline

    async def _assert_pipeline_exists(
        self, tenant_id: str, pipeline_id: int
    ) -> None:
        result = await self.db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.tenant_id == tenant_id,
                EngagementPipeline.id == pipeline_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise NotFoundError("Engagement-Pipeline", pipeline_id)

    async def get_by_id(
        self, tenant_id: str, campaign_id: int
    ) -> LeadgenCampaign:
        result = await self.db.execute(
            select(LeadgenCampaign).where(
                LeadgenCampaign.tenant_id == tenant_id,
                LeadgenCampaign.id == campaign_id,
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise NotFoundError("Leadgen-Kampagne", campaign_id)
        await self._attach_stats(tenant_id, [campaign])
        return campaign

    async def list_campaigns(
        self, tenant_id: str, status: str | None = None
    ) -> list[LeadgenCampaign]:
        stmt = select(LeadgenCampaign).where(LeadgenCampaign.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(LeadgenCampaign.status == status)
        stmt = stmt.order_by(LeadgenCampaign.created_at.desc())
        result = await self.db.execute(stmt)
        campaigns = list(result.scalars().all())
        await self._attach_stats(tenant_id, campaigns)
        return campaigns

    async def _attach_stats(
        self, tenant_id: str, campaigns: list[LeadgenCampaign]
    ) -> None:
        """Populate transient ``total_places``, ``enriched_places`` and
        ``active_run`` attributes on each campaign so the response schema
        can serialise them without a per-campaign round-trip."""
        if not campaigns:
            return
        ids = [c.id for c in campaigns]

        place_totals = (
            await self.db.execute(
                select(LeadgenPlace.campaign_id, func.count(LeadgenPlace.id))
                .where(
                    LeadgenPlace.tenant_id == tenant_id,
                    LeadgenPlace.campaign_id.in_(ids),
                )
                .group_by(LeadgenPlace.campaign_id)
            )
        ).all()
        total_by_id = {row[0]: row[1] for row in place_totals}

        enriched = (
            await self.db.execute(
                select(LeadgenPlace.campaign_id, func.count(LeadgenPlace.id))
                .where(
                    LeadgenPlace.tenant_id == tenant_id,
                    LeadgenPlace.campaign_id.in_(ids),
                    LeadgenPlace.status == "llm_done",
                )
                .group_by(LeadgenPlace.campaign_id)
            )
        ).all()
        enriched_by_id = {row[0]: row[1] for row in enriched}

        # Pick the most recent run per campaign that is still queued/running/paused.
        active_rows = (
            await self.db.execute(
                select(LeadgenRun)
                .where(
                    LeadgenRun.tenant_id == tenant_id,
                    LeadgenRun.campaign_id.in_(ids),
                    LeadgenRun.status.in_(["queued", "running", "paused"]),
                )
                .order_by(LeadgenRun.created_at.desc())
            )
        ).scalars().all()
        active_by_id: dict[int, dict] = {}
        for r in active_rows:
            if r.campaign_id in active_by_id:
                continue  # keep newest only
            ss = r.stage_state or {}
            active_by_id[r.campaign_id] = {
                "id": r.id,
                "status": r.status,
                "current_stage": r.current_stage,
                "processed": int(ss.get("places_processed", 0))
                or int(ss.get("api_calls_made", 0)),
                "total": int(ss.get("places_total", 0))
                or int(ss.get("max_override", 0)),
                "cost_cents": r.cost_cents or 0,
            }

        for c in campaigns:
            c.total_places = total_by_id.get(c.id, 0)
            c.enriched_places = enriched_by_id.get(c.id, 0)
            c.active_run = active_by_id.get(c.id)

    async def update(
        self, tenant_id: str, campaign_id: int, data: CampaignUpdate
    ) -> LeadgenCampaign:
        campaign = await self.get_by_id(tenant_id, campaign_id)

        if data.target_engagement_pipeline_id is not None:
            await self._assert_pipeline_exists(
                tenant_id, data.target_engagement_pipeline_id
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(campaign, field, value)

        await self.db.flush()
        await self.db.refresh(campaign)
        return campaign

    async def delete(self, tenant_id: str, campaign_id: int) -> None:
        campaign = await self.get_by_id(tenant_id, campaign_id)
        await self.db.delete(campaign)
        await self.db.flush()

    async def get_stats(
        self, tenant_id: str, campaign_id: int
    ) -> CampaignStats:
        await self.get_by_id(tenant_id, campaign_id)

        total = await self.db.execute(
            select(func.count(LeadgenPlace.id)).where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
            )
        )
        by_status_result = await self.db.execute(
            select(LeadgenPlace.status, func.count(LeadgenPlace.id))
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
            )
            .group_by(LeadgenPlace.status)
        )
        by_status = {row[0]: row[1] for row in by_status_result.all()}

        cost = await self.db.execute(
            select(func.coalesce(func.sum(LeadgenRun.cost_cents), 0)).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
            )
        )
        runs_total = await self.db.execute(
            select(func.count(LeadgenRun.id)).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
            )
        )
        runs_running = await self.db.execute(
            select(func.count(LeadgenRun.id)).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
                LeadgenRun.status == "running",
            )
        )

        return CampaignStats(
            campaign_id=campaign_id,
            total_places=total.scalar() or 0,
            by_status=by_status,
            total_cost_cents=cost.scalar() or 0,
            runs_total=runs_total.scalar() or 0,
            runs_running=runs_running.scalar() or 0,
        )


def _campaign_has_search_config(campaign: LeadgenCampaign) -> bool:
    """True if the campaign has enough config to start a places-stage run.

    Legacy path: queries list populated. Hybrid path: source_config has either
    nearby_types or text_synonyms.
    """
    if campaign.queries:
        return True
    cfg = campaign.source_config or {}
    return bool(cfg.get("nearby_types") or cfg.get("text_synonyms"))


class RunService:
    """Run lifecycle: queue, pause, resume, list. Actual work happens in worker."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def start(
        self, tenant_id: str, campaign_id: int
    ) -> LeadgenRun:
        """Queue a new run for a campaign.

        Fails if the campaign has no linked engagement pipeline, no queries,
        or another run is already running/queued.
        """
        campaign_svc = CampaignService(self.db)
        campaign = await campaign_svc.get_by_id(tenant_id, campaign_id)

        if not _campaign_has_search_config(campaign):
            raise ValidationError(
                "Kampagne hat keine Suchkonfiguration - bitte Suchbegriffe/Typen "
                "angeben (queries oder source_config.nearby_types/text_synonyms)"
            )
        if campaign.target_engagement_pipeline_id is None:
            raise ValidationError(
                "Kampagne hat keine Engagement-Pipeline verknuepft"
            )

        active = await self.db.execute(
            select(LeadgenRun).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
                LeadgenRun.status.in_(["queued", "running", "paused"]),
            )
        )
        if active.scalar_one_or_none():
            raise ValidationError(
                "Es laeuft bereits ein Run fuer diese Kampagne"
            )

        run = LeadgenRun(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            current_stage="places",
            status="queued",
            stage_state={},
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        if campaign.status == "draft":
            campaign.status = "active"
            await self.db.flush()

        logger.info(
            "Leadgen run queued: tenant={tenant} campaign={cid} run={rid}",
            tenant=tenant_id,
            cid=campaign_id,
            rid=run.id,
        )
        return run

    async def start_enrich(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        limit: int,
        sampling: str = "top_rated",
    ) -> LeadgenRun:
        """Queue an LLM-only run that skips Stage 1+2 and enriches existing places.

        The run starts directly at ``current_stage='llm'``. The worker uses
        ``stage_state['max_override']`` to cap processed places at ``limit``
        and ``stage_state['sampling']`` to choose between top-rated and random
        selection from the eligible pool (status in
        ('discovered','impressum_done','impressum_failed'), website not null,
        no llm_insights yet).

        Fails if another run is already running/queued for the campaign.
        """
        campaign_svc = CampaignService(self.db)
        campaign = await campaign_svc.get_by_id(tenant_id, campaign_id)

        active = await self.db.execute(
            select(LeadgenRun).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
                LeadgenRun.status.in_(["queued", "running", "paused"]),
            )
        )
        if active.scalar_one_or_none():
            raise ValidationError(
                "Es laeuft bereits ein Run fuer diese Kampagne"
            )

        run = LeadgenRun(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            current_stage="llm",
            status="queued",
            stage_state={
                "enrich_only": True,
                "max_override": int(limit),
                "sampling": sampling,
            },
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)

        if campaign.status == "draft":
            campaign.status = "active"
            await self.db.flush()

        logger.info(
            "Leadgen enrich-run queued: tenant={tenant} campaign={cid} "
            "run={rid} limit={limit} sampling={sampling}",
            tenant=tenant_id,
            cid=campaign_id,
            rid=run.id,
            limit=limit,
            sampling=sampling,
        )
        return run

    async def get_by_id(self, tenant_id: str, run_id: int) -> LeadgenRun:
        result = await self.db.execute(
            select(LeadgenRun).where(
                LeadgenRun.tenant_id == tenant_id, LeadgenRun.id == run_id
            )
        )
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundError("Leadgen-Run", run_id)
        return run

    async def list_for_campaign(
        self, tenant_id: str, campaign_id: int
    ) -> list[LeadgenRun]:
        result = await self.db.execute(
            select(LeadgenRun)
            .where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
            )
            .order_by(LeadgenRun.created_at.desc())
        )
        return list(result.scalars().all())

    async def pause(self, tenant_id: str, run_id: int) -> LeadgenRun:
        run = await self.get_by_id(tenant_id, run_id)
        if run.status not in ("queued", "running"):
            raise ValidationError(
                f"Run in Status '{run.status}' kann nicht pausiert werden"
            )
        run.status = "paused"
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def resume(
        self,
        tenant_id: str,
        run_id: int,
        *,
        additional_budget: int | None = None,
    ) -> LeadgenRun:
        run = await self.get_by_id(tenant_id, run_id)
        if run.status != "paused":
            raise ValidationError(
                f"Run in Status '{run.status}' kann nicht fortgesetzt werden"
            )

        if additional_budget and additional_budget > 0:
            campaign = await self.db.get(LeadgenCampaign, run.campaign_id)
            if campaign is None:
                raise NotFoundError("Campaign", run.campaign_id)
            cfg = dict(campaign.source_config or {})
            current_max = int(cfg.get("max_api_calls", 2000))
            cfg["max_api_calls"] = current_max + additional_budget
            campaign.source_config = cfg
            await self.db.flush()

        # If the run is paused after the places stage with tiles remaining,
        # flip current_stage back to "places" so the worker picks up the queue.
        if run.current_stage == "impressum_pending":
            ss = run.stage_state or {}
            if ss.get("tile_queue"):
                run.current_stage = "places"

        run.status = "queued"
        run.last_error = None
        run.completed_at = None
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def advance_stage(
        self, tenant_id: str, run_id: int
    ) -> LeadgenRun:
        """Advance run from `*_pending` stage to the actual stage + queue it.

        impressum_pending -> impressum
        llm_pending       -> llm
        """
        run = await self.get_by_id(tenant_id, run_id)
        if run.status != "paused":
            raise ValidationError(
                f"Run in Status '{run.status}' kann nicht fortgeschaltet werden"
            )
        mapping = {
            "impressum_pending": "impressum",
            "llm_pending": "llm",
        }
        new_stage = mapping.get(run.current_stage)
        if new_stage is None:
            raise ValidationError(
                f"Stage '{run.current_stage}' hat keinen nächsten Schritt"
            )

        # Reset the stage-scoped state so the new stage starts fresh.
        run.stage_state = {}
        run.current_stage = new_stage
        run.status = "queued"
        run.last_error = None
        run.completed_at = None
        await self.db.flush()
        await self.db.refresh(run)
        return run

    async def mark_running(self, run: LeadgenRun) -> None:
        """Called by worker when it picks up a queued run."""
        run.status = "running"
        if run.started_at is None:
            run.started_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(run)

    async def mark_failed(self, run: LeadgenRun, error: str) -> None:
        run.status = "failed"
        run.last_error = error
        await self.db.flush()
        await self.db.refresh(run)

    async def mark_completed(self, run: LeadgenRun) -> None:
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(run)


class PlaceService:
    """Read/reject places; creation happens inside the worker stage."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_campaign(
        self,
        tenant_id: str,
        campaign_id: int,
        status: str | None = None,
        page: int = 1,
        size: int = 50,
        order_by: str = "created_at",
        order_dir: str = "desc",
    ) -> tuple[list[LeadgenPlace], int]:
        base = select(LeadgenPlace).where(
            LeadgenPlace.tenant_id == tenant_id,
            LeadgenPlace.campaign_id == campaign_id,
        )
        if status:
            base = base.where(LeadgenPlace.status == status)

        total_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = total_result.scalar() or 0

        # Sortable columns mapped to ORM expressions. The match-score sits on
        # the joined LeadgenLLMInsights table; the rest live on LeadgenPlace.
        from app.leadgen.models import LeadgenLLMInsights as _Insights

        sort_map = {
            "name": (LeadgenPlace.name, False),
            "city": (LeadgenPlace.address_city, False),
            "status": (LeadgenPlace.status, False),
            "rating": (LeadgenPlace.rating, False),
            "match": (_Insights.target_match_score, True),  # join needed
            "created_at": (LeadgenPlace.created_at, False),
        }
        sort_col, needs_join = sort_map.get(order_by, sort_map["created_at"])
        direction = sort_col.desc() if order_dir == "desc" else sort_col.asc()
        # NULLS LAST for both directions so empty values don't dominate.
        direction = direction.nullslast()

        stmt = base.order_by(direction, LeadgenPlace.id.asc())
        if needs_join:
            stmt = stmt.outerjoin(
                _Insights, _Insights.place_id == LeadgenPlace.id
            )
        stmt = (
            stmt.offset((page - 1) * size)
            .limit(size)
            .options(
                selectinload(LeadgenPlace.impressum),
                selectinload(LeadgenPlace.llm_insights),
            )
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(
        self, tenant_id: str, place_id: int
    ) -> LeadgenPlace:
        result = await self.db.execute(
            select(LeadgenPlace)
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.id == place_id,
            )
            .options(
                selectinload(LeadgenPlace.impressum),
                selectinload(LeadgenPlace.llm_insights),
            )
        )
        place = result.scalar_one_or_none()
        if place is None:
            raise NotFoundError("Leadgen-Place", place_id)
        return place

    async def reject(
        self, tenant_id: str, place_id: int, reason: str
    ) -> LeadgenPlace:
        place = await self.get_by_id(tenant_id, place_id)
        place.status = "rejected"
        place.rejected_reason = reason
        await self.db.flush()
        await self.db.refresh(place)
        return place


_BUNDESLAND_BY_PLZ_PREFIX = {
    "0": "Sachsen / Sachsen-Anhalt / Thüringen",
    "1": "Berlin / Brandenburg / Mecklenburg-Vorpommern",
    "2": "Hamburg / Schleswig-Holstein / Niedersachsen",
    "3": "Niedersachsen / Nordrhein-Westfalen",
    "4": "Nordrhein-Westfalen",
    "5": "Nordrhein-Westfalen / Rheinland-Pfalz",
    "6": "Hessen / Rheinland-Pfalz / Saarland / Baden-Württemberg",
    "7": "Baden-Württemberg",
    "8": "Bayern",
    "9": "Bayern / Sachsen",
}


def _region_from_zip(zip_code: str | None) -> str:
    if not zip_code:
        return ""
    return _BUNDESLAND_BY_PLZ_PREFIX.get(zip_code[:1], "")


class LeadgenExportService:
    """LinkedIn Sales Navigator CSV exports (Account list + Lead list).

    Both exports share the same filter (min_score, only_enrolled, limit) so the
    counts in the preview match the actual download. The CSV layouts follow the
    column names Sales Navigator's bulk-uploader expects.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preview(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> dict:
        rows = await self._eligible(tenant_id, campaign_id, flt=flt)
        accounts = len(rows)
        leads = 0
        for _p, _ins, imp in rows:
            primary = _ins.primary_contact if _ins else None
            named = bool(primary and (primary.get("first_name") or primary.get("last_name")))
            extra = 0
            if imp and imp.managing_directors:
                extra = sum(
                    1 for n in imp.managing_directors if isinstance(n, str) and n.strip()
                )
            leads += max(extra, 1 if named else 0)
        return {"accounts_count": accounts, "leads_count": leads}

    async def build_accounts_csv(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> str:
        import csv
        import io

        rows = await self._eligible(tenant_id, campaign_id, flt=flt)
        buf = io.StringIO()
        # UTF-8 BOM so Excel opens the file with proper umlauts.
        buf.write("﻿")
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "Company Name",
                "Website",
                "Country",
                "Region",
                "Industry",
                "Match Score",
                "Notes",
            ]
        )
        for place, ins, _imp in rows:
            services = (ins.services if ins else []) or []
            industry = services[0] if services else "Elektroinstallation"
            notes = "; ".join(services[:3]) if services else ""
            writer.writerow(
                [
                    place.name,
                    place.website or "",
                    place.address_country or "DE",
                    _region_from_zip(place.address_zip),
                    industry,
                    ins.target_match_score if ins and ins.target_match_score is not None else "",
                    notes,
                ]
            )
        return buf.getvalue()

    async def build_leads_csv(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> str:
        import csv
        import io

        rows = await self._eligible(tenant_id, campaign_id, flt=flt)
        buf = io.StringIO()
        buf.write("﻿")
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "First Name",
                "Last Name",
                "Company",
                "Title",
                "Email",
                "Country",
                "Match Score",
                "Notes",
            ]
        )
        for place, ins, imp in rows:
            country = place.address_country or "DE"
            score = ins.target_match_score if ins and ins.target_match_score is not None else ""
            services = (ins.services if ins else []) or []
            notes = "; ".join(services[:3]) if services else ""
            email = (imp.email if imp else None) or ""

            written = False
            primary = ins.primary_contact if ins else None
            if primary and (primary.get("first_name") or primary.get("last_name")):
                writer.writerow(
                    [
                        primary.get("first_name") or "",
                        primary.get("last_name") or "",
                        place.name,
                        primary.get("role") or "Geschäftsführer",
                        email,
                        country,
                        score,
                        notes,
                    ]
                )
                written = True

            # Add extra rows for every managing_director that is not already the
            # primary contact (so Sales Nav can match more people per company).
            primary_full = (
                f"{(primary.get('first_name') or '').strip()} "
                f"{(primary.get('last_name') or '').strip()}".strip().lower()
                if primary
                else ""
            )
            for entry in (imp.managing_directors if imp else []) or []:
                if not isinstance(entry, str):
                    continue
                name = entry.strip()
                if not name:
                    continue
                if primary_full and name.lower() == primary_full:
                    continue
                first, _, last = name.partition(" ")
                writer.writerow(
                    [
                        first,
                        last or "",
                        place.name,
                        "Geschäftsführer",
                        email,
                        country,
                        score,
                        notes,
                    ]
                )
                written = True

            # Fallback: if neither primary_contact nor managing_directors gave
            # us a name we still emit one row with company-only info so the
            # firm can be looked up manually.
            if not written:
                writer.writerow(
                    [
                        "",
                        "",
                        place.name,
                        "",
                        email,
                        country,
                        score,
                        notes,
                    ]
                )
        return buf.getvalue()

    async def _eligible(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> list:
        from app.leadgen.models import (
            LeadgenImpressum,
            LeadgenLLMInsights,
            LeadgenPlace,
        )

        stmt = (
            select(LeadgenPlace, LeadgenLLMInsights, LeadgenImpressum)
            .join(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            )
            .outerjoin(
                LeadgenImpressum,
                LeadgenImpressum.place_id == LeadgenPlace.id,
            )
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenPlace.status == "llm_done",
                LeadgenLLMInsights.target_match_score >= flt.min_score,
            )
            .order_by(
                LeadgenLLMInsights.target_match_score.desc(),
                LeadgenPlace.rating.desc().nullslast(),
                LeadgenPlace.id.asc(),
            )
            .limit(flt.limit)
        )
        if flt.only_enrolled:
            stmt = stmt.where(LeadgenPlace.contact_id.isnot(None))
        result = await self.db.execute(stmt)
        return list(result.all())


class HandoffService:
    """Convert qualifying leadgen places into contacts and bulk-enroll them
    in the campaign's linked engagement pipeline.

    Workflow per place:
      1. Skip if no impressum email (we cannot reach the lead via email).
      2. Look up an existing Contact by (tenant_id, email); reuse if found.
      3. Otherwise create Company + Contact from impressum + primary_contact.
      4. Set place.contact_id so the same place is never handed off twice.
      5. Collect contact_ids and call EnrollmentService.bulk_enroll.

    The whole batch runs inside a single SQL transaction; the router commits
    on success.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def preview(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_score: int,
        limit: int,
    ) -> dict:
        """Return how many fresh places would be enrolled. Already-enrolled
        places are filtered out at SQL level so they never show up here."""
        rows = await self._eligible_query(
            tenant_id, campaign_id, min_score=min_score, limit=limit
        )
        with_email = sum(1 for _p, _ins, imp in rows if imp and imp.email)
        without_email = len(rows) - with_email
        return {
            "eligible_total": len(rows),
            "would_enroll": with_email,
            "already_have_contact": 0,
            "missing_email": without_email,
        }

    async def handoff(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_score: int,
        limit: int,
        pipeline_id: int | None = None,
    ) -> dict:
        """Execute the full handoff for the eligible places."""
        campaign_svc = CampaignService(self.db)
        campaign = await campaign_svc.get_by_id(tenant_id, campaign_id)

        target_pipeline_id = pipeline_id or campaign.target_engagement_pipeline_id
        if target_pipeline_id is None:
            raise ValidationError(
                "Kampagne hat keine Engagement-Pipeline verknüpft"
                " — bitte target_engagement_pipeline_id setzen"
            )
        await campaign_svc._assert_pipeline_exists(tenant_id, target_pipeline_id)

        rows = await self._eligible_query(
            tenant_id, campaign_id, min_score=min_score, limit=limit
        )

        contact_ids: list[int] = []
        skipped_no_email = 0
        skipped_existing = 0  # always 0 now (dedup happens at SQL level)
        contacts_created = 0
        contacts_reused = 0

        for place, _insights, impressum in rows:
            email = (impressum.email or "").strip().lower() if impressum else ""
            if not email:
                skipped_no_email += 1
                continue

            existing = (
                await self.db.execute(
                    select(Contact).where(
                        Contact.tenant_id == tenant_id,
                        Contact.email == email,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                contact = existing
                contacts_reused += 1
            else:
                contact = await self._build_contact_from_place(
                    tenant_id, place, _insights, impressum
                )
                contacts_created += 1

            place.contact_id = contact.id
            contact_ids.append(contact.id)

        await self.db.flush()

        if not contact_ids:
            return {
                "enrolled": 0,
                "skipped": 0,
                "errors": [],
                "contacts_created": contacts_created,
                "contacts_reused": contacts_reused,
                "skipped_no_email": skipped_no_email,
                "skipped_existing": skipped_existing,
                "pipeline_id": target_pipeline_id,
            }

        enroll_svc = EngagementEnrollmentService(self.db)
        result = await enroll_svc.bulk_enroll(
            tenant_id,
            BulkEnrollRequest(
                contact_ids=contact_ids,
                pipeline_id=target_pipeline_id,
                source_module="leadgen",
                source_campaign=campaign.slug,
            ),
        )

        return {
            "enrolled": result.enrolled,
            "skipped": result.skipped,
            "errors": list(result.errors),
            "contacts_created": contacts_created,
            "contacts_reused": contacts_reused,
            "skipped_no_email": skipped_no_email,
            "skipped_existing": skipped_existing,
            "pipeline_id": target_pipeline_id,
        }

    async def _eligible_query(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_score: int,
        limit: int,
    ) -> list:
        """Top N not-yet-handed-off enriched places sorted by match score.

        Filters ``place.contact_id IS NULL`` at the SQL level so subsequent
        handoff calls only see candidates that have not been enrolled before.
        That way wave-2 / wave-3 of the user clicking the button always digs
        into the next-best fresh leads without surfacing duplicates.
        """
        result = await self.db.execute(
            select(LeadgenPlace, LeadgenLLMInsights, LeadgenImpressum)
            .join(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            )
            .outerjoin(
                LeadgenImpressum,
                LeadgenImpressum.place_id == LeadgenPlace.id,
            )
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenPlace.status == "llm_done",
                LeadgenPlace.contact_id.is_(None),
                LeadgenLLMInsights.target_match_score >= min_score,
            )
            .order_by(
                LeadgenLLMInsights.target_match_score.desc(),
                LeadgenPlace.rating.desc().nullslast(),
                LeadgenPlace.id.asc(),
            )
            .limit(limit)
        )
        return list(result.all())

    async def _build_contact_from_place(
        self,
        tenant_id: str,
        place: LeadgenPlace,
        insights: LeadgenLLMInsights | None,
        impressum: LeadgenImpressum | None,
    ) -> Contact:
        """Create a Contact (and Company) from a leadgen place's data.

        Falls back gracefully when primary_contact is missing — uses the place
        name as contact name in that case so the handoff never crashes.
        """
        # 1. Find or create Company so contacts can be grouped by org.
        company = (
            await self.db.execute(
                select(Company).where(
                    Company.tenant_id == tenant_id,
                    Company.name == place.name,
                )
            )
        ).scalar_one_or_none()
        if company is None:
            company = Company(
                tenant_id=tenant_id,
                name=place.name,
                website=place.website,
                address={
                    "street": place.address_street,
                    "zip": place.address_zip,
                    "city": place.address_city,
                    "country": place.address_country,
                }
                if any(
                    [
                        place.address_street,
                        place.address_zip,
                        place.address_city,
                    ]
                )
                else None,
            )
            self.db.add(company)
            await self.db.flush()

        # 2. Build contact name from primary_contact when available.
        pc = insights.primary_contact if insights else None
        contact_name = place.name
        if pc:
            first = (pc.get("first_name") or "").strip()
            last = (pc.get("last_name") or "").strip()
            full = f"{first} {last}".strip()
            if full:
                contact_name = full

        email = (impressum.email or "").strip().lower() if impressum else ""
        phone = (impressum.phone if impressum else None) or place.phone

        contact = Contact(
            tenant_id=tenant_id,
            company_id=company.id,
            name=contact_name,
            email=email,
            phone=phone,
        )
        self.db.add(contact)
        await self.db.flush()
        return contact
