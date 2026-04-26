"""Leadgen worker - picks up queued runs and advances them stage by stage.

Currently implements Stage 1 (places discovery). Stages 2+ (impressum, LLM)
will be added incrementally. Each call to ``run_once`` processes at most one
run to keep restart behaviour predictable.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.leadgen.geo_tiling import (
    GeoTile,
    build_initial_tiles,
)
from app.leadgen.homepage_analyzer import (
    DEFAULT_PROMPT_TEMPLATE,
    LLMAnalysis,
    analyze_place_with_llm,
)
from app.leadgen.impressum_scraper import ImpressumData, fetch_impressum
from app.leadgen.models import (
    LeadgenCampaign,
    LeadgenImpressum,
    LeadgenLLMInsights,
    LeadgenPlace,
    LeadgenRun,
)
from app.leadgen.places_client import (
    NEARBY_MAX_RESULT_COUNT,
    GooglePlacesClient,
    ParsedPlace,
    PlacesApiError,
)
from app.leadgen.service import RunService
from app.leadgen.source_config import (
    GooglePlacesSourceConfig,
    ImpressumStageConfig,
    LLMStageConfig,
    parse_source_config,
)
from app.leadgen.stage_state import (
    STAGE_KEYS,
    mark_stage_completed,
    mark_stage_running,
    mark_stage_skipped,
    update_stage_counters,
)
from app.leadgen.website_verify import detect_booking_link, verify_no_website
from app.models.tenant import Tenant
from app.services.llm import LLMService
from app.services.tenant import TenantService

# Rough cost estimate for one Places Text Search request (new SKU, Pro tier).
# Real billing depends on field mask; this is a conservative default the admin
# can override by editing the run cost afterwards or tightening the mask.
DEFAULT_PLACES_COST_CENTS = 3

# We never process more than this many queries (= API-call bursts) in one
# worker invocation, so the event loop stays responsive and a single failing
# run cannot monopolise the worker.
MAX_QUERIES_PER_INVOCATION = 5

# Upper bound on API calls per run_once invocation in hybrid (tile) mode.
# Keeps the event loop responsive when a run has a big tile queue.
MAX_CALLS_PER_INVOCATION = 20

# Text Search returns at most 60 results across 3 pages; if a tile hits that,
# we consider it saturated and subdivide.
TEXT_SATURATION_THRESHOLD = 60

# Upper bound on places processed per worker invocation in the impressum stage.
# Keeps invocation bounded and gives the event loop a chance to breathe.
MAX_IMPRESSUM_PLACES_PER_INVOCATION = 50

# Same bound for the LLM stage. LLM calls are ~2-5s each, so with concurrency=5
# the invocation takes 20-50s wall-clock.
MAX_LLM_PLACES_PER_INVOCATION = 25


def _next_stage_for_mode(current: str, mode: str) -> str:
    """Resolve which stage runs after `current` for the given pipeline_mode.

    Returns "completed" when no more stages should run.
    """
    if current == "places":
        if mode == "smart":
            return "llm"
        return "impressum"  # cheap | legacy
    if current == "impressum":
        if mode == "legacy":
            return "llm"
        return "completed"  # cheap (and smart shouldn't reach here)
    if current == "llm":
        return "completed"
    return "completed"


def _transition_stage(run: LeadgenRun, mode: str) -> None:
    """Apply auto-chain transition after a stage reports completion.

    Active stages auto-chain (status=queued, with a fresh per-stage counter
    workspace BUT the ``stages`` history block preserved so the UI timeline
    keeps its context). Final stage maps to status=completed.
    """
    state = dict(run.stage_state or {})

    # Close out the stage that just finished. This is idempotent — if the
    # stage processor already marked it completed, this does nothing harmful.
    if run.current_stage in STAGE_KEYS:
        mark_stage_completed(state, run.current_stage)

    next_stage = _next_stage_for_mode(run.current_stage, mode)
    now = datetime.utcnow()

    if next_stage == "completed":
        # Mark stages that the chosen pipeline_mode bypassed as skipped, so
        # the timeline doesn't leave them as eternally "pending".
        _mark_unreached_stages_as_skipped(state, mode=mode)
        run.current_stage = "completed"
        run.status = "completed"
        run.completed_at = run.completed_at or now
        # Persist only the timeline; per-stage counter workspace is no longer
        # interesting once the run is closed.
        run.stage_state = {"stages": state.get("stages", {})}
        return

    # Auto-chain into next stage with fresh per-stage counters but preserved
    # timeline.
    run.current_stage = next_stage
    run.status = "queued"
    run.stage_state = {"stages": state.get("stages", {})}
    run.last_error = None
    run.completed_at = None


def _mark_unreached_stages_as_skipped(
    state: dict[str, Any], *, mode: str
) -> None:
    """At run completion, any stage in ``STAGE_KEYS`` that has no status entry
    yet was bypassed by the chosen pipeline mode — record that explicitly
    instead of leaving a blank row in the UI timeline."""
    block = state.get("stages")
    if not isinstance(block, dict):
        block = {}
        state["stages"] = block
    for key in STAGE_KEYS:
        entry = block.get(key)
        if isinstance(entry, dict) and entry.get("status"):
            continue
        mark_stage_skipped(state, key, reason=f"pipeline_mode={mode}")


async def _load_tenant_config(db: AsyncSession, tenant_id: str) -> dict:
    row = (
        await db.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
    ).scalar_one_or_none()
    return TenantService.merge_effective_config(
        tenant_id, (row.config or {}) if row else {}
    )


async def _upsert_places(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign: LeadgenCampaign,
    run: LeadgenRun,
    query: str,
    parsed: list[ParsedPlace],
) -> tuple[int, int]:
    """Insert new places, skip already-known google_place_ids.

    Returns (new_count, dup_count).
    """
    if not parsed:
        return 0, 0

    ids = [p.google_place_id for p in parsed if p.google_place_id]
    existing = await db.execute(
        select(LeadgenPlace.google_place_id).where(
            LeadgenPlace.tenant_id == tenant_id,
            LeadgenPlace.google_place_id.in_(ids),
        )
    )
    existing_ids = {row[0] for row in existing.all()}

    flag_no_calendar = bool(
        (campaign.source_config or {}).get("flag_no_calendar", False)
    )

    new_count = 0
    dup_count = 0
    for place in parsed:
        if not place.google_place_id:
            continue
        if place.google_place_id in existing_ids:
            dup_count += 1
            continue
        enrichment_flags: dict = {}
        if flag_no_calendar and not detect_booking_link(place.raw_payload or {}):
            enrichment_flags["no_calendar_in_google"] = True
        db.add(
            LeadgenPlace(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                run_id=run.id,
                source="google_places",
                source_record_id=place.google_place_id,
                google_place_id=place.google_place_id,
                source_query=query,
                name=place.name,
                address_street=place.address_street,
                address_zip=place.address_zip,
                address_city=place.address_city,
                address_country=place.address_country,
                formatted_address=place.formatted_address,
                lat=place.lat,
                lng=place.lng,
                website=place.website,
                phone=place.phone,
                google_categories=place.google_categories,
                rating=place.rating,
                user_ratings_total=place.user_ratings_total,
                business_status=place.business_status,
                raw_payload=place.raw_payload,
                status="discovered",
                enrichment_flags=enrichment_flags,
            )
        )
        new_count += 1
    return new_count, dup_count


# --------------------------------------------------------------------------
# Hybrid tile-based path (google_places source with nearby/text modes)
# --------------------------------------------------------------------------


def _tile_to_dict(t: GeoTile) -> dict[str, float]:
    return {"south": t.south, "west": t.west, "north": t.north, "east": t.east}


def _tile_from_dict(d: dict[str, float]) -> GeoTile:
    return GeoTile(south=d["south"], west=d["west"], north=d["north"], east=d["east"])


def _is_hybrid_config(cfg: GooglePlacesSourceConfig) -> bool:
    """True when the source_config has enough info to drive the tile crawler."""
    has_nearby = cfg.search_modes.nearby and bool(cfg.nearby_types)
    has_text = cfg.search_modes.text and bool(cfg.text_synonyms)
    return has_nearby or has_text


async def _crawl_tile(
    db: AsyncSession,
    *,
    tile: GeoTile,
    campaign: LeadgenCampaign,
    run: LeadgenRun,
    places_client: GooglePlacesClient,
    cfg: GooglePlacesSourceConfig,
    call_budget: int,
    max_pages_text: int,
    state: dict[str, Any],
    cost_cents_per_request: int,
) -> tuple[bool, int]:
    """Crawl one tile with the configured search modes.

    Returns (saturated, calls_made). Never makes more than ``call_budget``
    calls. Saturated means the tile returned so many results that we cannot
    be confident we got them all - the caller then subdivides.

    Increments ``state['api_calls_made']`` and ``run.cost_cents`` after every
    call so a mid-tile failure still leaves the accounting consistent.
    """
    calls = 0
    saturated = False

    def _record_call(places_count: int) -> None:
        nonlocal calls
        calls += 1
        state["api_calls_made"] = state.get("api_calls_made", 0) + 1
        run.cost_cents += cost_cents_per_request
        run.processed_count += places_count
        run.success_count += places_count

    if cfg.search_modes.nearby and cfg.nearby_types and calls < call_budget:
        center_lat, center_lng, radius_m = tile.inscribed_circle()
        page = await places_client.nearby_search(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_m=radius_m,
            included_types=cfg.nearby_types,
            language_code=cfg.language_code,
            region_code=cfg.region_code,
        )
        await _upsert_places(
            db,
            tenant_id=campaign.tenant_id,
            campaign=campaign,
            run=run,
            query=f"nearby:{','.join(cfg.nearby_types)}",
            parsed=page.places,
        )
        _record_call(len(page.places))
        if len(page.places) >= NEARBY_MAX_RESULT_COUNT:
            saturated = True

    if cfg.search_modes.text and cfg.text_synonyms:
        restriction = tile.to_rectangle_payload()
        for syn in cfg.text_synonyms:
            if calls >= call_budget:
                break
            total_for_syn = 0
            page_token: str | None = None
            for _page_idx in range(max_pages_text):
                if calls >= call_budget:
                    break
                page = await places_client.text_search(
                    syn,
                    language_code=cfg.language_code,
                    region_code=cfg.region_code,
                    page_token=page_token,
                    location_restriction=restriction,
                )
                await _upsert_places(
                    db,
                    tenant_id=campaign.tenant_id,
                    campaign=campaign,
                    run=run,
                    query=f"text:{syn}",
                    parsed=page.places,
                )
                _record_call(len(page.places))
                total_for_syn += len(page.places)
                if not page.next_page_token:
                    break
                page_token = page.next_page_token
            if total_for_syn >= TEXT_SATURATION_THRESHOLD:
                saturated = True

    return saturated, calls


async def _process_places_stage_hybrid(
    db: AsyncSession,
    *,
    run: LeadgenRun,
    campaign: LeadgenCampaign,
    places_client: GooglePlacesClient,
    cfg: GooglePlacesSourceConfig,
    max_pages_text: int,
    cost_cents_per_request: int,
) -> bool:
    """Tile-based hybrid crawl. Returns True when the tile queue is drained."""
    state: dict[str, Any] = dict(run.stage_state or {})
    mark_stage_running(state, "places")

    # First invocation: build initial tile queue
    if "tile_queue" not in state:
        initial = build_initial_tiles(
            scope=cfg.geographic.mode,
            bundesland=cfg.geographic.bundesland,
            center_lat=cfg.geographic.center_lat,
            center_lng=cfg.geographic.center_lng,
            radius_km=cfg.geographic.radius_km,
        )
        state["tile_queue"] = [_tile_to_dict(t) for t in initial]
        state["tiles_processed"] = 0
        state["api_calls_made"] = 0
        state["saturation_events"] = []

    invocation_calls = 0

    while (
        state["tile_queue"]
        and invocation_calls < MAX_CALLS_PER_INVOCATION
        and state.get("api_calls_made", 0) < cfg.max_api_calls
    ):
        tile_dict = state["tile_queue"].pop(0)
        tile = _tile_from_dict(tile_dict)

        global_budget = cfg.max_api_calls - state.get("api_calls_made", 0)
        invoc_budget = MAX_CALLS_PER_INVOCATION - invocation_calls
        budget = min(global_budget, invoc_budget)
        if budget <= 0:
            state["tile_queue"].insert(0, tile_dict)
            break

        try:
            saturated, calls = await _crawl_tile(
                db,
                tile=tile,
                campaign=campaign,
                run=run,
                places_client=places_client,
                cfg=cfg,
                call_budget=budget,
                max_pages_text=max_pages_text,
                state=state,
                cost_cents_per_request=cost_cents_per_request,
            )
        except PlacesApiError as e:
            run.error_count += 1
            run.last_error = f"Tile {tile_dict}: {e}"
            state["tile_queue"].insert(0, tile_dict)  # retry on next invocation
            run.stage_state = dict(state)
            raise

        invocation_calls += calls
        state["tiles_processed"] = state.get("tiles_processed", 0) + 1

        shorter_km = min(tile.width_km, tile.height_km)
        if saturated and shorter_km > cfg.min_tile_km:
            subs = tile.subdivide()
            state["tile_queue"].extend(_tile_to_dict(s) for s in subs)
            state["saturation_events"].append(
                {
                    "tile": tile_dict,
                    "split_into": len(subs),
                    "after_api_calls": state["api_calls_made"],
                }
            )

        state["tile_queue_len"] = len(state["tile_queue"])
        # Mirror tile/api stats into the timeline view.
        update_stage_counters(
            state,
            "places",
            set_values={
                "tiles_processed": state.get("tiles_processed", 0),
                "tile_queue_len": state.get("tile_queue_len", 0),
                "api_calls": state.get("api_calls_made", 0),
                "saturations": len(state.get("saturation_events") or []),
            },
        )
        run.stage_state = dict(state)
        await db.flush()

    budget_exhausted = state.get("api_calls_made", 0) >= cfg.max_api_calls
    if budget_exhausted and state["tile_queue"]:
        run.last_error = (
            f"max_api_calls ({cfg.max_api_calls}) reached, "
            f"{len(state['tile_queue'])} tiles remaining"
        )
    return len(state["tile_queue"]) == 0 or budget_exhausted


async def _scrape_one_place(
    place: LeadgenPlace,
    *,
    http_client: httpx.AsyncClient,
    cfg: ImpressumStageConfig,
    semaphore: asyncio.Semaphore,
) -> tuple[int, ImpressumData]:
    """Fetch + parse one Impressum under semaphore gate."""
    async with semaphore:
        data = await fetch_impressum(
            place.website,
            client=http_client,
            paths=tuple(cfg.paths_to_try),
            user_agent=cfg.user_agent,
            timeout_s=cfg.http_timeout_s,
        )
        return place.id, data


def _apply_impressum_to_place(
    place: LeadgenPlace,
    data: ImpressumData,
    *,
    existing: LeadgenImpressum | None,
) -> LeadgenImpressum:
    """Create or update the LeadgenImpressum record and bump place.status."""
    now = datetime.utcnow()
    record = existing or LeadgenImpressum(
        tenant_id=place.tenant_id,
        place_id=place.id,
    )
    record.source_url = data.source_url
    record.email = data.email
    record.phone = data.phone
    record.managing_directors = list(data.managing_directors)
    record.postal_address = data.postal_address
    record.handelsregister = data.handelsregister
    record.ust_id = data.ust_id
    record.extraction_error = data.error
    record.extracted_at = now

    has_any = bool(
        data.email or data.phone or data.managing_directors
        or data.handelsregister or data.ust_id
    )
    place.status = "impressum_done" if has_any else "impressum_failed"
    return record


async def _process_impressum_stage(
    db: AsyncSession,
    *,
    run: LeadgenRun,
    campaign: LeadgenCampaign,
    cfg: ImpressumStageConfig,
    http_client: httpx.AsyncClient,
) -> bool:
    """Scrape Impressum pages for `discovered` places in the campaign.

    Returns True when no more `discovered` places remain or the run budget for
    the stage is exhausted. Processes up to MAX_IMPRESSUM_PLACES_PER_INVOCATION
    per call so the worker stays responsive.
    """
    state: dict[str, Any] = dict(run.stage_state or {})
    mark_stage_running(state, "impressum")

    if "places_total" not in state:
        total = await db.scalar(
            select(func.count())
            .select_from(LeadgenPlace)
            .where(
                LeadgenPlace.campaign_id == campaign.id,
                LeadgenPlace.status == "discovered",
                LeadgenPlace.website.isnot(None),
            )
        )
        state["places_total"] = int(total or 0)
        state["places_processed"] = 0
        state["places_succeeded"] = 0
        state["places_failed"] = 0
        update_stage_counters(
            state, "impressum", set_values={"total": int(total or 0)}
        )

    remaining_budget = cfg.max_places_per_run - state.get("places_processed", 0)
    if remaining_budget <= 0:
        return True

    batch_size = min(MAX_IMPRESSUM_PLACES_PER_INVOCATION, remaining_budget)
    result = await db.execute(
        select(LeadgenPlace)
        .where(
            LeadgenPlace.campaign_id == campaign.id,
            LeadgenPlace.status == "discovered",
            LeadgenPlace.website.isnot(None),
        )
        .order_by(
            LeadgenPlace.rating.desc().nullslast(),
            LeadgenPlace.user_ratings_total.desc().nullslast(),
            LeadgenPlace.id.asc(),
        )
        .limit(batch_size)
    )
    batch = list(result.scalars().all())
    if not batch:
        return True

    place_ids = [p.id for p in batch]
    existing_rows = (
        await db.execute(
            select(LeadgenImpressum).where(LeadgenImpressum.place_id.in_(place_ids))
        )
    ).scalars().all()
    existing_by_place: dict[int, LeadgenImpressum] = {
        r.place_id: r for r in existing_rows
    }

    semaphore = asyncio.Semaphore(cfg.max_concurrency)
    tasks = [
        _scrape_one_place(
            p, http_client=http_client, cfg=cfg, semaphore=semaphore
        )
        for p in batch
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    places_by_id = {p.id: p for p in batch}
    for item in results:
        if isinstance(item, BaseException):
            logger.warning("impressum task crashed: {err}", err=str(item))
            state["places_processed"] = state.get("places_processed", 0) + 1
            state["places_failed"] = state.get("places_failed", 0) + 1
            update_stage_counters(
                state, "impressum", delta={"processed": 1, "failed": 1}
            )
            run.error_count += 1
            continue
        place_id, data = item
        place = places_by_id[place_id]
        record = _apply_impressum_to_place(
            place, data, existing=existing_by_place.get(place_id)
        )
        if record not in db.new:
            db.add(record)
        state["places_processed"] = state.get("places_processed", 0) + 1
        if data.error:
            state["places_failed"] = state.get("places_failed", 0) + 1
            update_stage_counters(
                state, "impressum", delta={"processed": 1, "failed": 1}
            )
            run.error_count += 1
        elif place.status == "impressum_done":
            state["places_succeeded"] = state.get("places_succeeded", 0) + 1
            update_stage_counters(
                state, "impressum", delta={"processed": 1, "succeeded": 1}
            )
            run.success_count += 1
            run.processed_count += 1
        else:
            state["places_failed"] = state.get("places_failed", 0) + 1
            update_stage_counters(
                state, "impressum", delta={"processed": 1, "failed": 1}
            )
            run.error_count += 1

    run.stage_state = dict(state)
    await db.flush()
    return False  # caller re-enters next invocation until no more discovered places


async def _analyze_one_place(
    place: LeadgenPlace,
    *,
    cfg: LLMStageConfig,
    http_client: httpx.AsyncClient,
    llm: LLMService,
    semaphore: asyncio.Semaphore,
    prompt_template: str,
) -> tuple[int, LLMAnalysis]:
    """Run one Stage-3 analysis under semaphore gate."""
    async with semaphore:
        data = await analyze_place_with_llm(
            website=place.website or "",
            target_profile=cfg.target_profile,
            output_description=cfg.output_description,
            prompt_template=prompt_template,
            model=cfg.model,
            provider=cfg.provider,
            llm_service=llm,
            http_client=http_client,
            paths=tuple(cfg.paths_to_fetch),
            user_agent=cfg.user_agent,
            timeout_s=cfg.http_timeout_s,
            max_html_chars=cfg.max_html_chars,
        )
        return place.id, data


def _apply_llm_analysis(
    place: LeadgenPlace,
    analysis: LLMAnalysis,
    existing: LeadgenLLMInsights | None,
) -> LeadgenLLMInsights:
    now = datetime.utcnow()
    record = existing or LeadgenLLMInsights(
        tenant_id=place.tenant_id,
        place_id=place.id,
    )
    record.target_match_score = analysis.target_match_score
    record.services = list(analysis.services)
    record.brands = list(analysis.brands)
    record.customer_segments = list(analysis.customer_segments)
    record.company_size_indicator = analysis.company_size_indicator
    record.personalization_hook = analysis.personalization_hook
    record.red_flags = list(analysis.red_flags)
    record.primary_contact = analysis.primary_contact
    record.pages_analyzed = list(analysis.pages_analyzed)
    record.input_tokens = analysis.input_tokens
    record.output_tokens = analysis.output_tokens
    record.cost_cents = analysis.cost_cents
    record.model_used = analysis.model_used
    record.extraction_error = analysis.error
    record.extracted_at = now

    if analysis.error:
        place.status = "llm_failed"
    elif analysis.target_match_score is not None:
        place.status = "llm_done"
    else:
        place.status = "llm_failed"
    return record


def _apply_impressum_from_llm(
    place: LeadgenPlace,
    impressum: LeadgenImpressum | None,
    llm_impressum: dict,
) -> LeadgenImpressum | None:
    """Apply LLM-extracted impressum data, preferring it over regex output.

    Strategy: LLM is the trusted source. Existing regex-extracted fields are
    only kept if the LLM did NOT return a value for that field. This wipes out
    junk like ['Herr'] or ['e Geschäftsführer'] when the LLM returns a clean
    name list.
    """
    if not llm_impressum:
        return impressum
    if impressum is None:
        impressum = LeadgenImpressum(
            tenant_id=place.tenant_id,
            place_id=place.id,
        )

    if llm_impressum.get("email"):
        impressum.email = str(llm_impressum["email"])[:320]
    if llm_impressum.get("phone"):
        impressum.phone = str(llm_impressum["phone"])[:50]
    # managing_directors: if LLM returned ANY (even empty), use it - it has
    # already been filtered by the analyzer's _is_real_person_name heuristic.
    if "managing_directors" in llm_impressum:
        directors = llm_impressum["managing_directors"]
        if isinstance(directors, list):
            impressum.managing_directors = [str(x)[:200] for x in directors[:5] if x]
    if llm_impressum.get("postal_address"):
        impressum.postal_address = str(llm_impressum["postal_address"])[:500]
    if llm_impressum.get("handelsregister"):
        impressum.handelsregister = str(llm_impressum["handelsregister"])[:100]
    if llm_impressum.get("ust_id"):
        impressum.ust_id = str(llm_impressum["ust_id"])[:50]

    if not impressum.extracted_at:
        impressum.extracted_at = datetime.utcnow()
    return impressum


async def _process_llm_stage(
    db: AsyncSession,
    *,
    run: LeadgenRun,
    campaign: LeadgenCampaign,
    cfg: LLMStageConfig,
    http_client: httpx.AsyncClient,
    llm: LLMService,
) -> bool:
    """Stage 3: fetch homepage + LLM analysis per place.

    Eligible places: status in ('impressum_done', 'impressum_failed', 'discovered')
    AND no llm_insights row yet. Places without a website skip the LLM call and
    receive a synthetic top-score record (no homepage = prime homepage-sales lead).
    """
    state: dict[str, Any] = dict(run.stage_state or {})
    mark_stage_running(state, "llm")

    eligible_statuses = ["impressum_done", "impressum_failed", "discovered"]

    # Enrich-only runs (started via /campaigns/{id}/runs/enrich) cap the run at
    # ``max_override`` and may use random instead of top-rated sampling.
    max_places = int(state.get("max_override") or cfg.max_places_per_run)
    sampling = state.get("sampling") or "top_rated"

    if "places_total" not in state:
        eligible_count = await db.scalar(
            select(func.count())
            .select_from(LeadgenPlace)
            .outerjoin(
                LeadgenLLMInsights, LeadgenLLMInsights.place_id == LeadgenPlace.id
            )
            .where(
                LeadgenPlace.campaign_id == campaign.id,
                LeadgenPlace.status.in_(eligible_statuses),
                LeadgenLLMInsights.id.is_(None),
            )
        )
        state["places_total"] = min(int(eligible_count or 0), max_places)
        state["places_processed"] = 0
        state["places_succeeded"] = 0
        state["places_failed"] = 0
        state["llm_cost_cents"] = 0
        update_stage_counters(
            state, "llm", set_values={"total": state["places_total"]}
        )

    remaining_budget = max_places - state.get("places_processed", 0)
    if remaining_budget <= 0:
        return True

    batch_size = min(MAX_LLM_PLACES_PER_INVOCATION, remaining_budget)

    if sampling == "random":
        order_clause = (func.random(),)
    else:
        order_clause = (
            LeadgenPlace.rating.desc().nullslast(),
            LeadgenPlace.user_ratings_total.desc().nullslast(),
            LeadgenPlace.id.asc(),
        )

    result = await db.execute(
        select(LeadgenPlace)
        .outerjoin(
            LeadgenLLMInsights, LeadgenLLMInsights.place_id == LeadgenPlace.id
        )
        .where(
            LeadgenPlace.campaign_id == campaign.id,
            LeadgenPlace.status.in_(eligible_statuses),
            LeadgenLLMInsights.id.is_(None),
        )
        .order_by(*order_clause)
        .limit(batch_size)
    )
    batch = list(result.scalars().all())
    if not batch:
        return True

    no_site_places = [p for p in batch if not (p.website and p.website.strip())]
    site_places = [p for p in batch if p.website and p.website.strip()]

    # Pre-LLM verify: for places Google Places didn't link a homepage to, run
    # one Serper search and see whether a non-portal domain plausibly matches
    # the business name. Hits get promoted to the normal LLM-analysis path
    # (with a sales-flag noting Google didn't have the homepage). Misses keep
    # the synthetic-top-score path below. Whole step degrades to no-op if the
    # SERPER_API_KEY is empty or the campaign disables it.
    if (
        no_site_places
        and cfg.verify_no_website_via_serper
        and settings.serper_api_key
    ):
        mark_stage_running(state, "verify")
        extra_blacklist = tuple(cfg.serper_blacklist_extra or ())
        promoted: list[LeadgenPlace] = []
        still_no_site: list[LeadgenPlace] = []
        for place in no_site_places:
            flags = dict(place.enrichment_flags or {})
            # Idempotency: if a previous run already verified this place,
            # respect that result.
            if flags.get("serper_checked_at"):
                still_no_site.append(place)
                continue
            found_url = await verify_no_website(
                name=place.name or "",
                city=place.address_city,
                serper_api_key=settings.serper_api_key,
                extra_blacklist=extra_blacklist,
            )
            flags["serper_checked_at"] = datetime.utcnow().isoformat()
            if found_url:
                place.website = found_url[:500]
                flags["homepage_not_in_google"] = True
                promoted.append(place)
                update_stage_counters(
                    state, "verify", delta={"checked": 1, "homepages_found": 1}
                )
            else:
                still_no_site.append(place)
                update_stage_counters(
                    state, "verify", delta={"checked": 1, "no_homepage": 1}
                )
            place.enrichment_flags = flags
        no_site_places = still_no_site
        site_places = list(site_places) + promoted

    # No-website places skip the LLM entirely: they ARE the prime homepage-sales
    # leads. We synthesise a max-score insights row and mark them llm_done.
    for place in no_site_places:
        synth = LLMAnalysis(
            target_match_score=10,
            personalization_hook="Kein eigener Webauftritt — Komplettangebot pitchen.",
            red_flags=["keine Homepage"],
            model_used="skip:no_website",
            cost_cents=0,
        )
        db.add(_apply_llm_analysis(place, synth, existing=None))
        state["places_processed"] = state.get("places_processed", 0) + 1
        state["places_succeeded"] = state.get("places_succeeded", 0) + 1
        update_stage_counters(
            state, "llm", delta={"processed": 1, "succeeded": 1, "skipped_no_site": 1}
        )
        run.success_count += 1
        run.processed_count += 1

    if not site_places:
        run.stage_state = dict(state)
        await db.flush()
        return False

    prompt_template = (cfg.prompt_template or DEFAULT_PROMPT_TEMPLATE).strip()
    # Sanity: template must have the two placeholders. Fall back if not.
    if "{target_profile}" not in prompt_template or "{content}" not in prompt_template:
        logger.warning(
            "LLM prompt template missing placeholders, falling back to default"
        )
        prompt_template = DEFAULT_PROMPT_TEMPLATE

    # Pre-load existing impressum records for fallback merge.
    place_ids = [p.id for p in site_places]
    existing_impressum = {
        r.place_id: r
        for r in (
            await db.execute(
                select(LeadgenImpressum).where(
                    LeadgenImpressum.place_id.in_(place_ids)
                )
            )
        ).scalars().all()
    }

    semaphore = asyncio.Semaphore(cfg.max_concurrency)
    tasks = [
        _analyze_one_place(
            p,
            cfg=cfg,
            http_client=http_client,
            llm=llm,
            semaphore=semaphore,
            prompt_template=prompt_template,
        )
        for p in site_places
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    places_by_id = {p.id: p for p in site_places}
    for item in results:
        if isinstance(item, BaseException):
            logger.warning("llm task crashed: {err}", err=str(item))
            state["places_processed"] = state.get("places_processed", 0) + 1
            state["places_failed"] = state.get("places_failed", 0) + 1
            update_stage_counters(
                state, "llm", delta={"processed": 1, "failed": 1}
            )
            run.error_count += 1
            continue
        place_id, analysis = item
        place = places_by_id[place_id]
        insights = _apply_llm_analysis(
            place, analysis, existing=None  # Would be pre-loaded if we supported re-runs.
        )
        db.add(insights)

        # Apply LLM-extracted impressum data (overrides junk regex output).
        merged_impressum = _apply_impressum_from_llm(
            place, existing_impressum.get(place.id), analysis.impressum_fallback
        )
        if merged_impressum is not None and merged_impressum not in db.new:
            db.add(merged_impressum)

        state["places_processed"] = state.get("places_processed", 0) + 1
        state["llm_cost_cents"] = state.get("llm_cost_cents", 0) + analysis.cost_cents
        run.cost_cents += analysis.cost_cents
        if analysis.error:
            state["places_failed"] = state.get("places_failed", 0) + 1
            update_stage_counters(
                state,
                "llm",
                delta={
                    "processed": 1,
                    "failed": 1,
                    "cost_cents": int(analysis.cost_cents or 0),
                },
            )
            run.error_count += 1
        else:
            state["places_succeeded"] = state.get("places_succeeded", 0) + 1
            update_stage_counters(
                state,
                "llm",
                delta={
                    "processed": 1,
                    "succeeded": 1,
                    "cost_cents": int(analysis.cost_cents or 0),
                },
            )
            run.success_count += 1
            run.processed_count += 1

    run.stage_state = dict(state)
    await db.flush()
    return False


async def _process_places_stage(
    db: AsyncSession,
    *,
    run: LeadgenRun,
    campaign: LeadgenCampaign,
    places_client: GooglePlacesClient,
    max_pages: int,
    cost_cents_per_request: int,
) -> bool:
    """Advance the ``places`` stage. Returns True when the stage is complete."""
    queries: list[str] = list(campaign.queries or [])
    state: dict[str, Any] = dict(run.stage_state or {})
    mark_stage_running(state, "places")
    idx = int(state.get("current_query_index", 0))

    if not queries:
        run.last_error = "Kampagne hat keine Queries"
        return True

    processed_this_invocation = 0

    while idx < len(queries) and processed_this_invocation < MAX_QUERIES_PER_INVOCATION:
        query = queries[idx]
        page_token: str | None = None
        pages_used = 0
        api_calls_for_query = 0

        try:
            while pages_used < max_pages:
                page = await places_client.text_search(
                    query,
                    language_code=campaign.language or "de",
                    region_code=campaign.region or "DE",
                    page_token=page_token,
                )
                api_calls_for_query += 1
                run.cost_cents += cost_cents_per_request
                new_count, dup_count = await _upsert_places(
                    db,
                    tenant_id=campaign.tenant_id,
                    campaign=campaign,
                    run=run,
                    query=query,
                    parsed=page.places,
                )
                run.processed_count += new_count + dup_count
                run.success_count += new_count
                update_stage_counters(
                    state,
                    "places",
                    delta={
                        "processed": new_count + dup_count,
                        "succeeded": new_count,
                        "cost_cents": cost_cents_per_request,
                        "api_calls": 1,
                    },
                )
                pages_used += 1
                if not page.next_page_token:
                    break
                page_token = page.next_page_token
        except PlacesApiError as e:
            run.error_count += 1
            run.last_error = f"Query '{query}': {e}"
            logger.error(
                "Places stage error tenant={t} run={r} query={q}: {err}",
                t=campaign.tenant_id,
                r=run.id,
                q=query,
                err=str(e),
            )
            raise

        idx += 1
        processed_this_invocation += 1
        state["current_query_index"] = idx
        state["last_query"] = query
        state["last_query_api_calls"] = api_calls_for_query
        run.stage_state = dict(state)
        await db.flush()

    return idx >= len(queries)


async def run_once(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: int,
    places_client_factory=None,
    cost_cents_per_request: int = DEFAULT_PLACES_COST_CENTS,
) -> dict:
    """Execute one batch of work for a specific run.

    The places_client_factory is injectable for tests. Production passes None
    and the worker builds a real GooglePlacesClient from tenant config.
    """
    run_svc = RunService(db)
    run = await run_svc.get_by_id(tenant_id, run_id)

    if run.status not in ("queued", "running"):
        return {"status": "skipped", "reason": f"run in status '{run.status}'"}

    campaign_result = await db.execute(
        select(LeadgenCampaign).where(
            LeadgenCampaign.tenant_id == tenant_id,
            LeadgenCampaign.id == run.campaign_id,
        )
    )
    campaign = campaign_result.scalar_one()

    await run_svc.mark_running(run)

    # Load tenant config once per invocation
    tenant_config = await _load_tenant_config(db, tenant_id)
    api_key = (
        tenant_config.get("google_places_api_key")
        or tenant_config.get("GOOGLE_PLACES_API_KEY")
    )
    max_pages = int(
        tenant_config.get("leadgen_max_places_pages_per_query", 3)
        or tenant_config.get("LEADGEN_MAX_PLACES_PAGES_PER_QUERY", 3)
        or 3
    )
    qps = int(
        tenant_config.get("leadgen_places_qps", 10)
        or tenant_config.get("LEADGEN_PLACES_QPS", 10)
        or 10
    )

    if places_client_factory is not None:
        client_ctx = places_client_factory()
    else:
        client_ctx = GooglePlacesClient(api_key=api_key or "", qps=qps)

    stage_completed = False
    try:
        if run.current_stage == "places":
            async with client_ctx as places_client:
                cfg = parse_source_config(
                    campaign.source or "google_places",
                    campaign.source_config or {},
                )
                if _is_hybrid_config(cfg):
                    stage_completed = await _process_places_stage_hybrid(
                        db,
                        run=run,
                        campaign=campaign,
                        places_client=places_client,
                        cfg=cfg,
                        max_pages_text=max_pages,
                        cost_cents_per_request=cost_cents_per_request,
                    )
                else:
                    stage_completed = await _process_places_stage(
                        db,
                        run=run,
                        campaign=campaign,
                        places_client=places_client,
                        max_pages=max_pages,
                        cost_cents_per_request=cost_cents_per_request,
                    )
        elif run.current_stage == "impressum":
            cfg_full = parse_source_config(
                campaign.source or "google_places",
                campaign.source_config or {},
            )
            async with httpx.AsyncClient(
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=cfg_full.impressum.max_concurrency * 2,
                    max_keepalive_connections=cfg_full.impressum.max_concurrency,
                ),
            ) as http_client:
                stage_completed = await _process_impressum_stage(
                    db,
                    run=run,
                    campaign=campaign,
                    cfg=cfg_full.impressum,
                    http_client=http_client,
                )
        elif run.current_stage == "llm":
            cfg_full = parse_source_config(
                campaign.source or "google_places",
                campaign.source_config or {},
            )
            llm_service = LLMService()
            async with httpx.AsyncClient(
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=cfg_full.llm.max_concurrency * 2,
                    max_keepalive_connections=cfg_full.llm.max_concurrency,
                ),
            ) as http_client:
                stage_completed = await _process_llm_stage(
                    db,
                    run=run,
                    campaign=campaign,
                    cfg=cfg_full.llm,
                    http_client=http_client,
                    llm=llm_service,
                )
        else:
            return {
                "status": "noop",
                "reason": f"stage '{run.current_stage}' not implemented yet",
            }
    except PlacesApiError as e:
        await run_svc.mark_failed(run, str(e))
        await db.commit()
        return {"status": "failed", "error": str(e)}
    except Exception as e:  # pragma: no cover - defensive
        await run_svc.mark_failed(run, f"Unerwarteter Fehler: {e}")
        await db.commit()
        raise

    if stage_completed:
        cfg_full = parse_source_config(
            campaign.source or "google_places",
            campaign.source_config or {},
        )
        _transition_stage(run, cfg_full.pipeline_mode)

    await db.commit()

    return {
        "status": "ok",
        "stage": run.current_stage,
        "run_status": run.status,
        "processed": run.processed_count,
        "success": run.success_count,
        "errors": run.error_count,
        "cost_cents": run.cost_cents,
        "stage_state": run.stage_state,
    }


async def run_loop(
    async_session_factory,
    *,
    poll_interval_seconds: float = 30.0,
    stop_after_empty_polls: int | None = None,
) -> None:
    """Long-running worker loop.

    Polls for queued/running runs across all tenants and processes them one at
    a time. Exits gracefully if ``stop_after_empty_polls`` is set and that many
    consecutive polls returned no work (useful for tests).
    """
    empty_polls = 0
    while True:
        async with async_session_factory() as db:
            result = await db.execute(
                select(LeadgenRun)
                .where(LeadgenRun.status.in_(["queued", "running"]))
                .order_by(LeadgenRun.created_at.asc())
                .limit(1)
            )
            run = result.scalar_one_or_none()
            if run is None:
                empty_polls += 1
                if stop_after_empty_polls and empty_polls >= stop_after_empty_polls:
                    logger.info("leadgen worker idle, exiting")
                    return
            else:
                empty_polls = 0
                try:
                    await run_once(db, tenant_id=run.tenant_id, run_id=run.id)
                except Exception as e:  # pragma: no cover
                    logger.exception(
                        "leadgen worker crashed on run={rid}: {err}",
                        rid=run.id,
                        err=str(e),
                    )

        await asyncio.sleep(poll_interval_seconds)
