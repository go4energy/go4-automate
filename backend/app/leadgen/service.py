"""Leadgen services - Campaign, Run, Place management."""

from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.contacts.models import Company, Contact
from app.contacts.utils import generate_tracking_hash
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
                channels=["letter", "email"],
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
                    LeadgenRun.status.in_(["queued", "running"]),
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
                # Only running/queued runs block — stopped runs can be resumed
                # later via /resume but don't lock the campaign for new starts.
                LeadgenRun.status.in_(["queued", "running"]),
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

    async def preview_enrich_eligible(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        stages: list[str] | None = None,
        min_match_score: int | None = None,
        apollo_validate_existing_urls: bool = False,
    ) -> dict:
        """Return how many places + contacts an enrich run with these params
        would touch. The frontend Run-Modal shows both numbers so the operator
        understands the linkedin stage hits Firmen *and* Personen.
        """
        # Force the campaign-existence check to surface a 404 early.
        await self.get_by_id_unscoped(tenant_id, campaign_id)
        # Apollo runs over leadgen_contacts, not places — return apollo_count
        # alongside the place/contact counts so the Run-Modal can show all
        # three numbers in a single API call.
        apollo_count = 0
        if stages and "apollo" in stages:
            apollo_count = await self._preview_apollo_eligible(
                tenant_id,
                campaign_id,
                min_match_score=min_match_score,
                validate_existing=apollo_validate_existing_urls,
            )
        if stages and "linkedin" in stages and "llm" not in stages:
            place_count = await self._preview_linkedin_eligible(
                tenant_id, campaign_id, min_match_score=min_match_score
            )
            contact_count = await self._preview_linkedin_contact_count(
                tenant_id, campaign_id, min_match_score=min_match_score
            )
        elif stages and stages == ["apollo"]:
            # Apollo-only run — places aren't iterated.
            place_count = 0
            contact_count = 0
        else:
            place_count = await self._preview_llm_eligible(
                tenant_id, campaign_id, min_match_score=min_match_score
            )
            contact_count = 0  # llm stage doesn't iterate contacts
        return {
            "eligible_count": place_count,
            "contact_count": contact_count,
            "apollo_count": apollo_count,
        }

    async def _preview_apollo_eligible(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_match_score: int | None,
        validate_existing: bool = False,
    ) -> int:
        """How many leadgen_contacts the Apollo stage would attempt to match.

        Filter mirrors the worker: contacts under campaign places, not yet
        Apollo-enriched, and (default) without an existing LinkedIn URL.
        ``validate_existing=True`` removes the URL filter so already-matched
        contacts also count — same as the worker's behaviour.
        """
        from app.leadgen.models import LeadgenContact

        stmt = (
            select(func.count(LeadgenContact.id))
            .select_from(LeadgenContact)
            .join(LeadgenPlace, LeadgenPlace.id == LeadgenContact.place_id)
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenContact.apollo_enriched_at.is_(None),
            )
        )
        if min_match_score is not None:
            stmt = stmt.join(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            ).where(LeadgenLLMInsights.target_match_score >= int(min_match_score))
        if not validate_existing:
            stmt = stmt.where(LeadgenContact.linkedin_url.is_(None))
        return int(await self.db.scalar(stmt) or 0)

    async def _preview_linkedin_contact_count(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_match_score: int | None,
    ) -> int:
        """How many leadgen_contacts under the eligible places.

        That's the per-person Serper-call count for the linkedin stage.
        """
        from app.leadgen.models import LeadgenContact

        stmt = (
            select(func.count(LeadgenContact.id))
            .select_from(LeadgenContact)
            .join(LeadgenPlace, LeadgenPlace.id == LeadgenContact.place_id)
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenPlace.status.in_(["impressum_done", "llm_done", "llm_failed"]),
            )
        )
        if min_match_score is not None:
            stmt = stmt.join(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            ).where(LeadgenLLMInsights.target_match_score >= int(min_match_score))
        return int(await self.db.scalar(stmt) or 0)

    async def get_by_id_unscoped(
        self, tenant_id: str, campaign_id: int
    ) -> LeadgenCampaign:
        result = await self.db.execute(
            select(LeadgenCampaign).where(
                LeadgenCampaign.tenant_id == tenant_id,
                LeadgenCampaign.id == campaign_id,
            )
        )
        c = result.scalar_one_or_none()
        if c is None:
            raise NotFoundError("Leadgen-Kampagne", campaign_id)
        return c

    async def _preview_linkedin_eligible(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_match_score: int | None,
    ) -> int:
        # The worker filters in-Python on enrichment_flags, so we replicate
        # the SQL parts here and let the operator see the *upper bound* —
        # places that already carry linkedin_processed_at would still be
        # skipped at run time. We accept the slight overcount because the
        # alternative is a JSONB has-key op that breaks SQLite tests.
        stmt = (
            select(func.count(LeadgenPlace.id))
            .select_from(LeadgenPlace)
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenPlace.status.in_(["impressum_done", "llm_done", "llm_failed"]),
            )
        )
        if min_match_score is not None:
            stmt = stmt.join(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            ).where(LeadgenLLMInsights.target_match_score >= int(min_match_score))
        return int(await self.db.scalar(stmt) or 0)

    async def _preview_llm_eligible(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_match_score: int | None,
    ) -> int:
        stmt = (
            select(func.count(LeadgenPlace.id))
            .select_from(LeadgenPlace)
            .outerjoin(
                LeadgenLLMInsights,
                LeadgenLLMInsights.place_id == LeadgenPlace.id,
            )
            .where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.campaign_id == campaign_id,
                LeadgenPlace.status.in_(
                    ["discovered", "impressum_done", "impressum_failed"]
                ),
                LeadgenLLMInsights.id.is_(None),
            )
        )
        # min_match_score on a not-yet-llm-scored pool is by definition empty;
        # the operator is asking for "Top-X leads to re-LLM" only when stages
        # explicitly include 'llm'. We honour the filter literally so the
        # number reflects what the worker will actually do.
        if min_match_score is not None:
            stmt = stmt.where(
                LeadgenLLMInsights.target_match_score >= int(min_match_score)
            )
        return int(await self.db.scalar(stmt) or 0)

    async def start_enrich(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        limit: int,
        sampling: str = "top_rated",
        stages: list[str] | None = None,
        min_match_score: int | None = None,
        enrich_companies: bool = False,
        apollo_validate_existing_urls: bool = False,
        apollo_reveal_email: bool = False,
        apollo_reveal_phone: bool = False,
    ) -> LeadgenRun:
        """Queue an enrichment run that skips Google Places and runs the
        selected ``stages`` on the existing place pool.

        ``stages`` (subset of impressum/verify/llm/linkedin) is the new
        contract introduced with the Run-Modal — the run starts at the first
        listed stage and ``stage_state['explicit_stages']`` drives the auto-
        chain in ``worker._transition_stage``. When ``stages`` is None we
        fall back to the legacy "verify+llm" behaviour so existing callers
        keep working.

        Fails if another run is already running/queued for the campaign.
        """
        campaign_svc = CampaignService(self.db)
        campaign = await campaign_svc.get_by_id(tenant_id, campaign_id)

        active = await self.db.execute(
            select(LeadgenRun).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.campaign_id == campaign_id,
                # Only running/queued runs block — stopped runs can be resumed
                # later via /resume but don't lock the campaign for new starts.
                LeadgenRun.status.in_(["queued", "running"]),
            )
        )
        if active.scalar_one_or_none():
            raise ValidationError(
                "Es laeuft bereits ein Run fuer diese Kampagne"
            )

        # Validate the stages subset against the canonical order.
        from app.leadgen.stage_state import STAGE_KEYS

        valid_stage_set = set(STAGE_KEYS)
        explicit_stages = list(stages) if stages else None
        if explicit_stages:
            unknown = [s for s in explicit_stages if s not in valid_stage_set]
            if unknown:
                raise ValidationError(
                    f"Unbekannte Stage(s): {unknown}. Erlaubt: {list(STAGE_KEYS)}"
                )
            if "places" in explicit_stages:
                raise ValidationError(
                    "'places' ist im Enrich-Run nicht erlaubt — "
                    "nutze stattdessen den vollen Pipeline-Run."
                )
            # Pick the first stage in canonical order to start at.
            start_stage = next(s for s in STAGE_KEYS if s in explicit_stages)
        else:
            # Legacy behaviour: start at LLM, no explicit-stages marker so
            # _transition_stage uses pipeline_mode-based defaults.
            start_stage = "llm"

        initial_state: dict = {
            "enrich_only": True,
            "max_override": int(limit),
            "sampling": sampling,
        }
        if explicit_stages:
            initial_state["explicit_stages"] = explicit_stages
        if min_match_score is not None:
            initial_state["min_match_score"] = int(min_match_score)
        if enrich_companies:
            initial_state["enrich_companies"] = True
        if apollo_validate_existing_urls:
            initial_state["apollo_validate_existing_urls"] = True
        if apollo_reveal_email:
            initial_state["apollo_reveal_email"] = True
        if apollo_reveal_phone:
            initial_state["apollo_reveal_phone"] = True

        run = LeadgenRun(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            current_stage=start_stage,
            status="queued",
            stage_state=initial_state,
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

    async def stop(self, tenant_id: str, run_id: int) -> LeadgenRun:
        """Halt a running/queued run.

        Unlike the legacy ``pause`` semantics, ``stopped`` does NOT block new
        runs on the same campaign — the operator can immediately start a
        fresh run (e.g. with corrected filters) without first having to
        resume or abort. The stopped run can still be resumed via ``resume``
        as long as no other run is currently active on the campaign.
        """
        run = await self.get_by_id(tenant_id, run_id)
        if run.status not in ("queued", "running"):
            raise ValidationError(
                f"Run in Status '{run.status}' kann nicht gestoppt werden"
            )
        run.status = "stopped"
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
        # ``paused`` kept for backward-compat with any old DB rows; new code
        # always emits ``stopped``.
        if run.status not in ("stopped", "paused"):
            raise ValidationError(
                f"Run in Status '{run.status}' kann nicht fortgesetzt werden"
            )

        # Guard against starting a second concurrent run when another one is
        # already active on the campaign (the operator started a fresh run
        # after stopping this one — resuming would create a race).
        other_active = (
            await self.db.execute(
                select(LeadgenRun).where(
                    LeadgenRun.tenant_id == tenant_id,
                    LeadgenRun.campaign_id == run.campaign_id,
                    LeadgenRun.status.in_(["queued", "running"]),
                    LeadgenRun.id != run.id,
                )
            )
        ).scalar_one_or_none()
        if other_active is not None:
            raise ValidationError(
                f"Ein anderer Run (#{other_active.id}) läuft bereits — "
                "stoppe diesen zuerst oder warte bis er fertig ist."
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
                # ``contacts`` is part of PlaceResponse — eager-load to avoid
                # MissingGreenlet errors when Pydantic validates the relation.
                selectinload(LeadgenPlace.contacts),
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
                selectinload(LeadgenPlace.contacts),
            )
        )
        place = result.scalar_one_or_none()
        if place is None:
            raise NotFoundError("Leadgen-Place", place_id)
        return place

    async def neighbors(
        self,
        tenant_id: str,
        place_id: int,
        *,
        order_by: str = "match",
        order_dir: str = "desc",
        status: str | None = None,
    ) -> dict:
        """Return the prev/next place ids for the same campaign + sort + filter.

        Used by the detail view's forward/backward arrows so the operator can
        walk through the prospect list without bouncing to the campaign view.
        Returns ``{"prev_id": int|None, "next_id": int|None}``.
        """
        from app.leadgen.models import LeadgenLLMInsights as _Insights

        # Resolve the campaign by loading the place once.
        place = await self.get_by_id(tenant_id, place_id)

        sort_map = {
            "name": (LeadgenPlace.name, False),
            "city": (LeadgenPlace.address_city, False),
            "status": (LeadgenPlace.status, False),
            "rating": (LeadgenPlace.rating, False),
            "match": (_Insights.target_match_score, True),
            "created_at": (LeadgenPlace.created_at, False),
        }
        sort_col, needs_join = sort_map.get(order_by, sort_map["created_at"])
        is_desc = order_dir == "desc"

        base = select(LeadgenPlace.id, sort_col).where(
            LeadgenPlace.tenant_id == tenant_id,
            LeadgenPlace.campaign_id == place.campaign_id,
        )
        if status:
            base = base.where(LeadgenPlace.status == status)
        if needs_join:
            base = base.outerjoin(
                _Insights, _Insights.place_id == LeadgenPlace.id
            )
        # Stable secondary sort by id so identical primary-sort values still
        # produce a deterministic walk.
        primary = sort_col.desc() if is_desc else sort_col.asc()
        primary = primary.nullslast()
        ordered = base.order_by(primary, LeadgenPlace.id.asc())

        rows = (await self.db.execute(ordered)).all()
        ids_in_order = [row[0] for row in rows]
        try:
            idx = ids_in_order.index(place_id)
        except ValueError:
            return {"prev_id": None, "next_id": None}
        prev_id = ids_in_order[idx - 1] if idx > 0 else None
        next_id = ids_in_order[idx + 1] if idx + 1 < len(ids_in_order) else None
        return {"prev_id": prev_id, "next_id": next_id}

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
        from app.leadgen.models import LeadgenContact

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
        # Apollo counts ``leadgen_contacts`` rows directly (one per person we
        # already materialised). Falls back to ``leads`` when the linkedin
        # stage hasn't run yet so the export-modal still shows a useful number.
        apollo = 0
        apollo_with_linkedin = 0
        if rows:
            place_ids = [p.id for p, _ins, _imp in rows]
            apollo = int(
                await self.db.scalar(
                    select(func.count())
                    .select_from(LeadgenContact)
                    .where(LeadgenContact.place_id.in_(place_ids))
                )
                or 0
            )
            apollo_with_linkedin = int(
                await self.db.scalar(
                    select(func.count())
                    .select_from(LeadgenContact)
                    .where(
                        LeadgenContact.place_id.in_(place_ids),
                        LeadgenContact.linkedin_url.isnot(None),
                    )
                )
                or 0
            )
        return {
            "accounts_count": accounts,
            "leads_count": leads,
            "apollo_count": apollo or leads,
            "apollo_with_linkedin": apollo_with_linkedin,
        }

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

    async def preview_apollo(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> int:
        """Return how many rows the Apollo CSV export would emit for ``flt``.

        Apollo wants one row per *person*, so we count ``leadgen_contacts``
        rows whose place is in the eligible pool — not places.
        """
        from app.leadgen.models import LeadgenContact

        rows = await self._eligible(tenant_id, campaign_id, flt=flt)
        if not rows:
            return 0
        place_ids = [p.id for p, _ins, _imp in rows]
        result = await self.db.execute(
            select(func.count())
            .select_from(LeadgenContact)
            .where(LeadgenContact.place_id.in_(place_ids))
        )
        return int(result.scalar() or 0)

    async def build_apollo_csv(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        flt,
    ) -> str:
        """Apollo-formatted CSV for direct upload via 'Import a CSV of Contacts'.

        One row per leadgen_contacts entry, joined to the place + LLM insights
        for industry / city. Empty cells are fine — Apollo matches on any
        combination of name, company, website, email, LinkedIn URL.
        """
        import csv
        import io

        from app.leadgen.models import LeadgenContact

        rows = await self._eligible(tenant_id, campaign_id, flt=flt)
        buf = io.StringIO()
        # UTF-8 BOM so Excel opens umlauts correctly.
        buf.write("﻿")
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "First Name",
                "Last Name",
                "Title",
                "Email",
                "Contact LinkedIn URL",
                "Company",
                "Website",
                "Company LinkedIn URL",
                "City",
                "State",
                "Country",
                "Industry",
                "Notes",
            ]
        )
        if not rows:
            return buf.getvalue()

        place_ids = [p.id for p, _ins, _imp in rows]
        contact_rows = (
            await self.db.execute(
                select(LeadgenContact)
                .where(LeadgenContact.place_id.in_(place_ids))
                .order_by(LeadgenContact.place_id.asc(), LeadgenContact.id.asc())
            )
        ).scalars().all()
        contacts_by_place: dict[int, list[LeadgenContact]] = {}
        for c in contact_rows:
            contacts_by_place.setdefault(c.place_id, []).append(c)

        place_lookup = {p.id: (p, ins, imp) for p, ins, imp in rows}
        for place_id, contacts in contacts_by_place.items():
            place, ins, _imp = place_lookup[place_id]
            services = (ins.services if ins else []) or []
            industry = services[0] if services else "Elektroinstallation"
            notes = "; ".join(services[:3]) if services else ""
            country = place.address_country or "DE"
            for contact in contacts:
                writer.writerow(
                    [
                        contact.first_name or "",
                        contact.last_name or "",
                        contact.role or "",
                        contact.email or "",
                        contact.linkedin_url or "",
                        place.name,
                        place.website or "",
                        place.linkedin_company_url or "",
                        place.address_city or "",
                        _region_from_zip(place.address_zip),
                        country,
                        industry,
                        notes,
                    ]
                )
        return buf.getvalue()


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
        include_without_email: bool = True,
    ) -> dict:
        """Return how many fresh places would be enrolled. Already-enrolled
        places are filtered out at SQL level so they never show up here.

        ``include_without_email=True`` (default) counts email-less places
        as enrollable too — they get a synthetic placeholder email and
        become reachable via Letter/Phone.
        """
        rows = await self._eligible_query(
            tenant_id, campaign_id, min_score=min_score, limit=limit
        )
        with_email = sum(1 for _p, _ins, imp in rows if imp and imp.email)
        without_email = len(rows) - with_email
        would_enroll = len(rows) if include_without_email else with_email
        return {
            "eligible_total": len(rows),
            "would_enroll": would_enroll,
            "already_have_contact": 0,
            "missing_email": without_email,
            "would_enroll_without_email": (
                without_email if include_without_email else 0
            ),
        }

    async def handoff(
        self,
        tenant_id: str,
        campaign_id: int,
        *,
        min_score: int,
        limit: int,
        pipeline_id: int | None = None,
        include_without_email: bool = True,
    ) -> dict:
        """Execute the full handoff for the eligible places.

        ``include_without_email=True`` lets places without an impressum
        email through with a synthetic placeholder email so they can be
        reached via Letter/Phone. The placeholder is stable per place id
        (``noemail-{place_id}@placeholder.go4automate.local``) so re-runs
        are idempotent.
        """
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
        enrolled_without_email = 0

        for place, _insights, impressum in rows:
            real_email = (impressum.email or "").strip().lower() if impressum else ""
            if not real_email:
                if not include_without_email:
                    skipped_no_email += 1
                    continue
                # Synthetic placeholder so the Contact NOT NULL constraint
                # holds. Stable per place so re-runs find the same row.
                email = f"noemail-{place.id}@placeholder.go4automate.local"
                is_synthetic_email = True
            else:
                email = real_email
                is_synthetic_email = False

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
                # Idempotent hash assignment: a contact that was imported via
                # CSV / created via /tracking/identify already has a hash and
                # we never overwrite it. Only fill the gap when missing so the
                # outreach URLs can carry the tracking parameter.
                if not contact.tracking_hash:
                    contact.tracking_hash = generate_tracking_hash()
            else:
                contact = await self._build_contact_from_place(
                    tenant_id, place, _insights, impressum,
                    override_email=email if is_synthetic_email else None,
                )
                contacts_created += 1

            if is_synthetic_email:
                enrolled_without_email += 1

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
                "enrolled_without_email": enrolled_without_email,
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
            "enrolled_without_email": enrolled_without_email,
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
        *,
        override_email: str | None = None,
    ) -> Contact:
        """Create a Contact (and Company) from a leadgen place's data.

        Prefers a ``leadgen_contacts`` row when one exists (carries
        LinkedIn URL + gender). Falls back to ``primary_contact`` JSON or the
        place name when no contact rows have been materialised yet.
        """
        from app.leadgen.models import LeadgenContact

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
                linkedin_url=place.linkedin_company_url,
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
        elif place.linkedin_company_url and not company.linkedin_url:
            # Backfill LinkedIn URL on a previously-handed-off company so a
            # later linkedin-stage rerun still propagates the data.
            company.linkedin_url = place.linkedin_company_url

        # 2. Pick the best person record. Prefer the leadgen_contacts row that
        # came out of the linkedin stage (has gender + LinkedIn URL); fall back
        # to primary_contact JSON; then to the place name.
        leadgen_contact: LeadgenContact | None = (
            await self.db.execute(
                select(LeadgenContact)
                .where(
                    LeadgenContact.place_id == place.id,
                    LeadgenContact.is_handed_off.is_(False),
                )
                .order_by(LeadgenContact.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()

        contact_name = place.name
        first = ""
        last = ""
        position: str | None = None
        linkedin_url: str | None = None
        gender: str | None = None
        gender_confidence: float | None = None

        if leadgen_contact is not None:
            first = (leadgen_contact.first_name or "").strip()
            last = (leadgen_contact.last_name or "").strip()
            full = (f"{first} {last}".strip()) or leadgen_contact.full_name
            if full:
                contact_name = full
            position = leadgen_contact.role
            linkedin_url = leadgen_contact.linkedin_url
            gender = leadgen_contact.gender
            gender_confidence = leadgen_contact.gender_confidence
        else:
            pc = insights.primary_contact if insights else None
            if pc:
                first = (pc.get("first_name") or "").strip()
                last = (pc.get("last_name") or "").strip()
                full = f"{first} {last}".strip()
                if full:
                    contact_name = full
                position = pc.get("role")

        # ``override_email`` lets the handoff path inject a synthetic
        # placeholder when the impressum has no email and the user opted
        # into "include without email". The contact stays addressable
        # via Letter / Phone.
        if override_email is not None:
            email = override_email
        else:
            email = (impressum.email or "").strip().lower() if impressum else ""
        phone = (impressum.phone if impressum else None) or place.phone

        custom_fields: dict = {}
        if gender:
            custom_fields["gender"] = gender
        if gender_confidence is not None:
            custom_fields["gender_confidence"] = gender_confidence

        contact = Contact(
            tenant_id=tenant_id,
            company_id=company.id,
            name=contact_name,
            email=email,
            phone=phone,
            position=position,
            linkedin=linkedin_url[:200] if linkedin_url else None,
            custom_fields=custom_fields,
            source="leadgen",
            tags=["leadgen"],
            # Single source of truth shared with /tracking/identify and the
            # CSV import path — the partial UNIQUE index on
            # contacts.tracking_hash guarantees no collision.
            tracking_hash=generate_tracking_hash(),
        )
        self.db.add(contact)
        await self.db.flush()

        if leadgen_contact is not None:
            leadgen_contact.is_handed_off = True
            leadgen_contact.contact_id = contact.id
        return contact
