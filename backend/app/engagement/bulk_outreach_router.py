"""Endpoints for the bulk Brain-driven outreach loop.

Mounted under /v1/engagement.
"""

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.engagement.bulk_outreach import (
    mass_replace_in_drafts,
    regenerate_action,
    run_bulk_brain,
)
from app.engagement.models import (
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
)
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/engagement", tags=["engagement-bulk"])


# ─── Request schemas ────────────────────────────────────────────────


class BulkBrainRunRequest(BaseModel):
    channel: str = Field(default="email")
    slot: str = Field(default="initial")
    limit: int | None = None
    model_override: str | None = None  # e.g. "claude-opus-4-7" for A/B compare


class BulkApproveRequest(BaseModel):
    action_ids: list[int]


class BulkRegenerateRequest(BaseModel):
    action_ids: list[int]
    model_override: str | None = None


class MassReplaceRequest(BaseModel):
    find: str
    replace: str
    fields: list[str] | None = None  # default: subject+body


class BulkBrainStatusResponse(BaseModel):
    status: str
    total: int = 0
    done: int = 0
    cache_read_total: int = 0
    cache_create_total: int = 0
    input_total: int = 0
    output_total: int = 0
    errors: list = []
    started_at: str | None = None
    finished_at: str | None = None
    channel: str | None = None
    slot: str | None = None
    model: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ─── Stale-detection schema ──────────────────────────────────────────


class DraftSummary(BaseModel):
    action_id: int
    contact_id: int
    enrollment_id: int
    contact_name: str | None
    company_name: str | None
    subject: str
    body_excerpt: str
    slot: str
    model_used: str | None
    ab_variant: str | None  # 'A' or 'B' if generated via A/B-Run, else None
    is_stale: bool
    generated_at: str | None
    insights_updated_at: str | None

    model_config = ConfigDict(from_attributes=True)


# ─── Bulk-Brain-Run ──────────────────────────────────────────────────


async def _run_bulk_brain_in_background(
    tenant_id: str,
    tenant_config: dict,
    pipeline_id: int,
    channel: str,
    slot: str,
    limit: int | None,
    model_override: str | None,
) -> None:
    """Wrapper that opens its own DB session — we can't use the request's
    session inside a background task because it gets closed when the
    HTTP response is returned."""
    async with async_session() as db:
        try:
            await run_bulk_brain(
                db=db,
                tenant_id=tenant_id,
                tenant_config=tenant_config,
                pipeline_id=pipeline_id,
                channel=channel,
                slot=slot,
                limit=limit,
                model_override=model_override,
            )
        except Exception as exc:
            logger.exception(
                "Bulk-Brain background task failed: pipeline={pid} err={err}",
                pid=pipeline_id,
                err=str(exc),
            )
            # Mark status as failed
            try:
                p = (
                    await db.execute(
                        select(EngagementPipeline).where(
                            EngagementPipeline.id == pipeline_id
                        )
                    )
                ).scalar_one_or_none()
                if p:
                    s = dict(p.bulk_brain_status or {})
                    s["status"] = "failed"
                    s["error"] = str(exc)[:500]
                    p.bulk_brain_status = s
                    await db.commit()
            except Exception:
                pass


@router.post(
    "/pipelines/{pipeline_id}/brain/run-bulk",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_bulk_brain(
    pipeline_id: int,
    data: BulkBrainRunRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Kick off the bulk Brain run as a background task. Returns immediately
    with the pipeline id. Poll the status endpoint to track progress."""
    # Sanity: pipeline exists
    p = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline nicht gefunden")
    # Don't double-trigger
    cur = p.bulk_brain_status or {}
    if cur.get("status") == "running":
        raise HTTPException(
            409,
            f"Bulk-Run läuft bereits ({cur.get('done', 0)}/{cur.get('total', '?')})",
        )

    background_tasks.add_task(
        _run_bulk_brain_in_background,
        tenant_id=tenant_id,
        tenant_config=tenant_config,
        pipeline_id=pipeline_id,
        channel=data.channel,
        slot=data.slot,
        limit=data.limit,
        model_override=data.model_override,
    )
    return {"pipeline_id": pipeline_id, "status": "queued"}


@router.get(
    "/pipelines/{pipeline_id}/brain/status",
    response_model=BulkBrainStatusResponse,
)
async def get_bulk_brain_status(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkBrainStatusResponse:
    p = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline nicht gefunden")
    s = p.bulk_brain_status or {"status": "idle"}
    return BulkBrainStatusResponse(**s)


@router.post("/pipelines/{pipeline_id}/brain/stop")
async def stop_bulk_brain(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Setzt das Cancel-Flag — der Bulk-Loop bricht beim nächsten Commit
    (alle 5 Drafts) sauber ab. Bisherige Drafts bleiben in der DB.
    """
    p = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline nicht gefunden")
    cur = dict(p.bulk_brain_status or {})
    if cur.get("status") != "running":
        return {"ok": True, "noop": True, "current": cur.get("status", "idle")}
    cur["status"] = "cancel_requested"
    p.bulk_brain_status = cur
    await db.commit()
    return {"ok": True, "noop": False, "done": cur.get("done", 0), "total": cur.get("total", 0)}


# ─── Drafts listing (with stale detection) ───────────────────────────


@router.get(
    "/pipelines/{pipeline_id}/drafts",
    response_model=list[DraftSummary],
)
async def list_drafts(
    pipeline_id: int,
    channel: str = "email",
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[DraftSummary]:
    """List all ready_for_approval drafts for a pipeline + channel.

    Stale-detection: if leadgen_llm_insights for the contact were updated
    after the draft was generated, we mark ``is_stale=True``.
    """
    from sqlalchemy.orm import selectinload

    from app.leadgen.models import LeadgenLLMInsights

    stmt = (
        select(PendingAction)
        .options(selectinload(PendingAction.contact))
        .where(
            PendingAction.tenant_id == tenant_id,
            PendingAction.pipeline_id == pipeline_id,
            PendingAction.module == channel,
            PendingAction.status == "ready_for_approval",
        )
        .order_by(PendingAction.id)
    )
    actions = list((await db.execute(stmt)).scalars().all())
    out: list[DraftSummary] = []
    for action in actions:
        try:
            payload = json.loads(action.suggested_content or "{}")
        except json.JSONDecodeError:
            payload = {}
        subject = payload.get("llm_subject", "") if isinstance(payload, dict) else ""
        body = payload.get("llm_body", "") if isinstance(payload, dict) else ""

        contact = action.contact
        # Stale detection: compare insights.updated_at with action.created_at
        is_stale = False
        insights_updated = None
        if contact and contact.leadgen_place_id:
            ins = (
                await db.execute(
                    select(LeadgenLLMInsights).where(
                        LeadgenLLMInsights.place_id == contact.leadgen_place_id
                    )
                )
            ).scalar_one_or_none()
            if ins:
                insights_updated = ins.updated_at.isoformat() if ins.updated_at else None
                if ins.updated_at and ins.updated_at > action.created_at:
                    is_stale = True

        # Resolve company name for display (best-effort)
        company_name = None
        if contact and contact.company_id:
            from app.contacts.models import Company

            company = (
                await db.execute(
                    select(Company).where(Company.id == contact.company_id)
                )
            ).scalar_one_or_none()
            if company:
                company_name = company.name

        ctx = action.context or {}
        out.append(
            DraftSummary(
                action_id=action.id,
                contact_id=action.contact_id,
                enrollment_id=action.enrollment_id,
                contact_name=contact.name if contact else None,
                company_name=company_name,
                subject=subject,
                body_excerpt=(body[:300] + "…") if len(body) > 300 else body,
                slot=ctx.get("slot", "initial"),
                model_used=ctx.get("model_used"),
                ab_variant=ctx.get("ab_variant"),
                is_stale=is_stale,
                generated_at=ctx.get("generated_at"),
                insights_updated_at=insights_updated,
            )
        )
    # Sort: by contact (so A/B variants of the same recipient sit together),
    # then by ab_variant (A before B), then newest first.
    out.sort(
        key=lambda d: (
            d.contact_id,
            d.ab_variant or "",
            -(d.action_id),
        )
    )
    return out


# ─── Bulk approve / regenerate / mass-replace ────────────────────────


@router.post("/actions/bulk/approve")
async def bulk_approve(
    data: BulkApproveRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve pending_actions and trigger send via Default-Provider in background.

    Setzt Status auf 'approved' (synchron), startet dann einen BackgroundTask
    der jede Action rendert + via SendGrid versendet + Status auf 'sent' / 'failed'
    setzt. Antwort kommt sofort zurück; UI-Polling über GET /actions/{id} zeigt
    den Fortschritt pro Action.
    """
    if not data.action_ids:
        return {"approved": 0, "queued": 0}
    stmt = select(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.id.in_(data.action_ids),
        PendingAction.status == "ready_for_approval",
    )
    actions = list((await db.execute(stmt)).scalars().all())
    approved_ids = []
    for a in actions:
        a.status = "approved"
        approved_ids.append(a.id)
    await db.commit()

    if approved_ids:
        background_tasks.add_task(
            _send_approved_actions_in_background,
            tenant_id=tenant_id,
            tenant_config=tenant_config,
            action_ids=approved_ids,
        )

    return {"approved": len(actions), "queued": len(approved_ids)}


async def _send_approved_actions_in_background(
    tenant_id: str,
    tenant_config: dict,
    action_ids: list[int],
) -> None:
    """Render + send each approved action via the active Email-Provider.

    Iteriert sequentiell (Rate-Limit-freundlich). Pro Action:
    - render_for_action() → fertige Subject + HTML
    - get_provider() → erste aktive Provider-Instanz für den Tenant
    - provider.send_email() → SendGrid v3 API
    - status = 'sent' bei Erfolg, 'failed' bei Fehler
    """
    from app.emailmarketing.models import EmailUnsubscribe
    from app.emailmarketing.providers import EmailMessage, get_provider
    from app.emailmarketing.render_service import render_for_action
    from app.emailmarketing.service import EmailProviderService

    async with async_session() as db:
        # Get default (first active) provider for this tenant
        provider_service = EmailProviderService(db)
        providers = await provider_service.list_providers(tenant_id)
        active = [p for p in providers if p.status == "active"]
        if not active:
            logger.error(
                "Kein aktiver Email-Provider für tenant {tid} — actions {ids} bleiben approved",
                tid=tenant_id, ids=action_ids,
            )
            return
        provider_model = active[0]
        provider = get_provider(provider_model)

        # Suppression-List einmal pro Run laden — nach Unsubscribe-Klicks
        # werden diese Adressen NIE mehr angeschrieben.
        unsubscribed = {
            row[0]
            for row in (await db.execute(
                select(EmailUnsubscribe.email).where(
                    EmailUnsubscribe.tenant_id == tenant_id
                )
            )).all()
        }

        for aid in action_ids:
            action = (await db.execute(
                select(PendingAction).where(PendingAction.id == aid)
            )).scalar_one_or_none()
            if not action:
                continue
            # Idempotenz-Lock: Nur Actions im Zustand 'approved' verarbeiten.
            # Status sofort auf 'sending' flippen + commit, BEVOR der Provider-
            # Call rausgeht. Damit kann ein zweiter Trigger des gleichen Loops
            # nicht doppelt senden, weil er die Action dann nicht mehr in
            # 'approved' findet.
            if action.status != "approved":
                logger.warning(
                    "Action {aid} skipped — status={s} (already processed?)",
                    aid=aid, s=action.status,
                )
                continue
            action.status = "sending"
            await db.commit()
            try:
                rendered = await render_for_action(db, action, tenant_config)
                # Suppression-Check: Empfänger hat sich abgemeldet → skip
                if rendered["contact_email"] in unsubscribed:
                    action.status = "suppressed"
                    ctx = dict(action.context or {})
                    ctx["suppressed_at"] = _now_iso_send()
                    ctx["suppressed_reason"] = "unsubscribed"
                    action.context = ctx
                    await db.commit()
                    logger.info(
                        "Action {aid} skipped — recipient {to} unsubscribed",
                        aid=aid, to=rendered["contact_email"],
                    )
                    continue
                # tracking_token = action.id als String. SendGrid gibt das
                # in jedem Webhook-Event zurück (custom_args), damit wir
                # Bounces/Spam-Reports direkt der Action zuordnen können.
                msg = EmailMessage(
                    to_email=rendered["contact_email"],
                    to_name=rendered.get("contact_name"),
                    subject=rendered["subject"],
                    html_content=rendered["html"],
                    text_content=rendered.get("text") or "",
                    tracking_token=str(action.id),
                )
                result = await provider.send_email(msg)
                if result.success:
                    action.status = "sent"
                    ctx = dict(action.context or {})
                    ctx["sent_at"] = _now_iso_send()
                    ctx["sent_via_provider_id"] = provider_model.id
                    ctx["sent_message_id"] = result.message_id
                    action.context = ctx
                    logger.info(
                        "Action {aid} versendet an {to}",
                        aid=aid, to=rendered["contact_email"],
                    )
                else:
                    action.status = "failed"
                    ctx = dict(action.context or {})
                    ctx["send_error"] = (result.error or "")[:500]
                    action.context = ctx
                    logger.error(
                        "Action {aid} send failed: {err}",
                        aid=aid, err=result.error,
                    )
                await db.commit()
            except Exception as exc:
                logger.exception("Send failed für action {aid}", aid=aid)
                action.status = "failed"
                ctx = dict(action.context or {})
                ctx["send_error"] = str(exc)[:500]
                action.context = ctx
                await db.commit()


def _now_iso_send() -> str:
    from datetime import datetime as _dt
    return _dt.utcnow().isoformat() + "Z"


@router.post("/actions/bulk/regenerate")
async def bulk_regenerate(
    data: BulkRegenerateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Regenerate the LLM body for many drafts (e.g. after Prompt edits or
    insights refresh). Runs sequentially to keep the cache warm."""
    if not data.action_ids:
        return {"regenerated": 0}
    stmt = select(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.id.in_(data.action_ids),
        PendingAction.status.in_(["ready_for_approval", "cancelled"]),
    )
    actions = list((await db.execute(stmt)).scalars().all())
    n_done = 0
    for a in actions:
        try:
            await regenerate_action(
                db=db,
                tenant_id=tenant_id,
                tenant_config=tenant_config,
                action=a,
                model_override=data.model_override,
            )
            n_done += 1
        except Exception:
            logger.exception("Regenerate failed for action {aid}", aid=a.id)
            # leave the row untouched
    return {"regenerated": n_done}


class BulkDeleteRequest(BaseModel):
    action_ids: list[int]


@router.post("/actions/bulk/delete")
async def bulk_delete_actions(
    data: BulkDeleteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete the given pending_actions. Used to wipe drafts before
    rerunning the Brain with fresh prompts. Sister-call to bulk-approve
    + bulk-regenerate."""
    if not data.action_ids:
        return {"deleted": 0}
    stmt = delete(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.id.in_(data.action_ids),
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"deleted": result.rowcount or 0}


@router.delete("/pipelines/{pipeline_id}/drafts")
async def delete_all_drafts(
    pipeline_id: int,
    channel: str = "email",
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Wipe ALL ready_for_approval drafts for this pipeline+channel.
    Hard reset to start a fresh Bulk-Run."""
    stmt = delete(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.pipeline_id == pipeline_id,
        PendingAction.module == channel,
        PendingAction.status == "ready_for_approval",
    )
    result = await db.execute(stmt)
    await db.commit()
    return {"deleted": result.rowcount or 0}


@router.post("/pipelines/{pipeline_id}/drafts/mass-replace")
async def mass_replace(
    pipeline_id: int,
    data: MassReplaceRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Find/replace text across all open email drafts in a pipeline."""
    try:
        return await mass_replace_in_drafts(
            db=db,
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            find=data.find,
            replace=data.replace,
            fields=data.fields,
        )
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ─── A/B variant generation ──────────────────────────────────────────


class ABGenerateRequest(BaseModel):
    channel: str = "email"
    slot: str = "initial"
    variant_b_model: str = "claude-opus-4-7"  # B with stronger model
    limit: int | None = None


@router.post("/pipelines/{pipeline_id}/brain/run-ab")
async def trigger_ab_brain(
    pipeline_id: int,
    data: ABGenerateRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate two drafts per enrollment — variant A with the prompt's default
    model, variant B with ``variant_b_model``. Both drafts land as separate
    pending_actions tagged in the context with ``ab_variant``: 'A' / 'B'.

    User can then approve only the variant they prefer per recipient.
    """
    p = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Pipeline nicht gefunden")

    background_tasks.add_task(
        _run_ab_in_background,
        tenant_id=tenant_id,
        tenant_config=tenant_config,
        pipeline_id=pipeline_id,
        channel=data.channel,
        slot=data.slot,
        variant_b_model=data.variant_b_model,
        limit=data.limit,
    )
    return {"pipeline_id": pipeline_id, "status": "queued", "ab": True}


async def _run_ab_in_background(
    tenant_id: str,
    tenant_config: dict,
    pipeline_id: int,
    channel: str,
    slot: str,
    variant_b_model: str,
    limit: int | None,
) -> None:
    """Run two bulk passes back-to-back so the static prompt cache stays
    warm across both variants — but each enrollment ends up with two
    drafts tagged A/B. Phase A populates bulk_brain_status (model = default),
    phase B keeps writing the same status row with phase='B' and
    model = variant_b_model so the UI sees one continuous run."""
    async with async_session() as db:
        # Phase A — default model
        try:
            await run_bulk_brain(
                db=db,
                tenant_id=tenant_id,
                tenant_config=tenant_config,
                pipeline_id=pipeline_id,
                channel=channel,
                slot=slot,
                limit=limit,
                model_override=None,
            )
        except Exception as exc:
            logger.exception("A/B variant A failed: {err}", err=str(exc))
        # Tag the A-variant drafts so we know which is which.
        await _tag_recent_drafts_with_variant(db, tenant_id, pipeline_id, channel, "A")
        # Phase B — alternate model, generated for each A draft.
        await _generate_variant_b(
            db=db,
            tenant_id=tenant_id,
            tenant_config=tenant_config,
            pipeline_id=pipeline_id,
            channel=channel,
            slot=slot,
            variant_b_model=variant_b_model,
            limit=limit,
        )


async def _tag_recent_drafts_with_variant(
    db: AsyncSession, tenant_id: str, pipeline_id: int, channel: str, variant: str
) -> None:
    """Mark all currently ready_for_approval drafts of this pipeline+channel
    that don't yet carry an ab_variant tag with the given letter."""
    stmt = select(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.pipeline_id == pipeline_id,
        PendingAction.module == channel,
        PendingAction.status == "ready_for_approval",
    )
    rows = list((await db.execute(stmt)).scalars().all())
    for a in rows:
        ctx = dict(a.context or {})
        if "ab_variant" not in ctx:
            ctx["ab_variant"] = variant
            a.context = ctx
    await db.commit()


async def _generate_variant_b(
    db: AsyncSession,
    tenant_id: str,
    tenant_config: dict,
    pipeline_id: int,
    channel: str,
    slot: str,
    variant_b_model: str,
    limit: int | None,
) -> None:
    """Iterate the A-variant drafts and produce a B-variant for each
    using the alternate model."""
    from app.engagement.bulk_outreach import (
        _resolve_prompt,
        generate_for_enrollment,
    )

    stmt = select(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.pipeline_id == pipeline_id,
        PendingAction.module == channel,
        PendingAction.status == "ready_for_approval",
    )
    actions = list((await db.execute(stmt)).scalars().all())
    actions = [
        a for a in actions if (a.context or {}).get("ab_variant") == "A"
    ]
    if limit:
        actions = actions[:limit]

    pipeline = (
        await db.execute(
            select(EngagementPipeline).where(EngagementPipeline.id == pipeline_id)
        )
    ).scalar_one()
    prompt = await _resolve_prompt(
        db, tenant_id, pipeline_id, channel, slot
    )

    # Status auf running-Phase-B setzen (continuous run für die UI)
    from datetime import datetime as _dt
    b_status = dict(pipeline.bulk_brain_status or {})
    b_status.update({
        "status": "running",
        "phase": "B",
        "model": variant_b_model,
        "total": len(actions),
        "done": 0,
        "started_at": b_status.get("started_at") or _dt.utcnow().isoformat() + "Z",
        "finished_at": None,
        "errors": b_status.get("errors") or [],
    })
    pipeline.bulk_brain_status = b_status
    await db.commit()

    for a in actions:
        enrollment = (
            await db.execute(
                select(PipelineEnrollment).where(
                    PipelineEnrollment.id == a.enrollment_id
                )
            )
        ).scalar_one_or_none()
        if not enrollment:
            continue
        try:
            fields, usage = await generate_for_enrollment(
                db=db,
                tenant_id=tenant_id,
                tenant_config=tenant_config,
                enrollment=enrollment,
                pipeline=pipeline,
                prompt=prompt,
                model_override=variant_b_model,
            )
            content_payload = {
                "llm_subject": fields.get("llm_subject", ""),
                "llm_body": fields.get("llm_body", ""),
                "_raw": fields.get("_raw", ""),
                "_model": fields.get("_model", ""),
                "_prompt_id": prompt.id,
                "_slot": slot,
            }
            new_action = PendingAction(
                tenant_id=tenant_id,
                contact_id=a.contact_id,
                pipeline_id=pipeline_id,
                enrollment_id=a.enrollment_id,
                module=channel,
                action_type=a.action_type,
                context={
                    **(a.context or {}),
                    "ab_variant": "B",
                    "model_used": variant_b_model,
                    "duration_ms": fields.get("_duration_ms", 0),
                    "generated_at": (a.context or {}).get("generated_at"),
                },
                suggested_content=json.dumps(content_payload, ensure_ascii=False),
                priority="normal",
                needs_approval=True,
                status="ready_for_approval",
            )
            db.add(new_action)
            await db.flush()
            # Status fortschreiben damit UI Progress-Bar weiterläuft
            b_status["done"] = b_status.get("done", 0) + 1
            b_status["cache_read_total"] = b_status.get("cache_read_total", 0) + int(
                usage.get("cache_read_input_tokens", 0)
            )
            b_status["cache_create_total"] = b_status.get("cache_create_total", 0) + int(
                usage.get("cache_creation_input_tokens", 0)
            )
            b_status["input_total"] = b_status.get("input_total", 0) + int(
                usage.get("input_tokens", 0)
            )
            b_status["output_total"] = b_status.get("output_total", 0) + int(
                usage.get("output_tokens", 0)
            )
            if b_status["done"] % 5 == 0 or b_status["done"] == len(actions):
                pipeline.bulk_brain_status = dict(b_status)
                await db.commit()
        except Exception as exc:
            logger.exception("A/B variant B failed for action {aid}", aid=a.id)
            b_status.setdefault("errors", []).append({
                "action_id": a.id, "error": str(exc)[:300]
            })

    b_status["status"] = "done"
    b_status["phase"] = "B"
    b_status["finished_at"] = _dt.utcnow().isoformat() + "Z"
    pipeline.bulk_brain_status = dict(b_status)
    await db.commit()


# ─── Preview rendered email ──────────────────────────────────────────


class ActionPreviewResponse(BaseModel):
    subject: str
    html: str
    text: str
    template_id: int | None
    contact_email: str
    contact_name: str | None
    personalized: dict
    is_stale: bool = False


@router.get("/actions/{action_id}/preview", response_model=ActionPreviewResponse)
async def preview_action(
    action_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> ActionPreviewResponse:
    """Render the email for a pending_action and return the final HTML
    + subject. Re-callable; uses current template state."""
    from app.emailmarketing.render_service import render_for_action
    from app.leadgen.models import LeadgenLLMInsights

    a = (
        await db.execute(
            select(PendingAction).where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Action nicht gefunden")
    try:
        rendered = await render_for_action(db, a, tenant_config)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    # Stale detection (same logic as list_drafts)
    is_stale = False
    from app.contacts.models import Contact

    contact = (
        await db.execute(select(Contact).where(Contact.id == a.contact_id))
    ).scalar_one_or_none()
    if contact and contact.leadgen_place_id:
        ins = (
            await db.execute(
                select(LeadgenLLMInsights).where(
                    LeadgenLLMInsights.place_id == contact.leadgen_place_id
                )
            )
        ).scalar_one_or_none()
        if ins and ins.updated_at and ins.updated_at > a.created_at:
            is_stale = True
    return ActionPreviewResponse(**rendered, is_stale=is_stale)


# Single regenerate (handy for the "Neu generieren" button per draft)


@router.post("/actions/{action_id}/regenerate")
async def regenerate_single(
    action_id: int,
    model_override: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    a = (
        await db.execute(
            select(PendingAction).where(
                PendingAction.id == action_id,
                PendingAction.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Action nicht gefunden")
    return await regenerate_action(
        db=db,
        tenant_id=tenant_id,
        tenant_config=tenant_config,
        action=a,
        model_override=model_override,
    )


# Helper to await asyncio sleep needed somewhere — placeholder import
_ = asyncio  # silence "unused" if kept for future-stream use
