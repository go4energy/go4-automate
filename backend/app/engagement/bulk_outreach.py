"""Bulk outreach content generation.

For a given pipeline + channel + slot, this iterates all enrollments
without an active draft and asks the LLM to produce structured output
(``{llm_subject, llm_body}``) per recipient. Results land as
``pending_actions`` rows ready for human review (or auto-approval if
the pipeline opts in).

The LLM call uses Anthropic ephemeral caching — the system prompt is
identical across all enrollments in a single run, so only the variable
values per recipient are billed at full rate.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.context_loader import get_contact_context
from app.contacts.models import Contact
from app.customer_journey.service import CampaignService, RefCodeService
from app.engagement.models import (
    EngagementPipeline,
    PendingAction,
    PipelineEnrollment,
    PipelinePrompt,
)
from app.engagement.prompts_router import (
    _build_outreach_variables,
    _split_prompt_for_caching,
)
from app.exceptions import NotFoundError, ValidationError
from app.services.llm import LLMService, get_default_model

# ─────────────────────────────────────────────────────────────────────
# Output parsing
# ─────────────────────────────────────────────────────────────────────

# Brain prompts produce blocks like:
#   BETREFF: <subject>
#   EROEFFNUNG: <text>
# (we match BETREFF/EROEFFNUNG/EINSTIEG case-insensitively)
_FIELD_RE = re.compile(
    r"^(BETREFF|EROEFFNUNG|EINSTIEG|EINSTIEGSTEXT|SUBJECT|BODY)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_brain_output(text: str) -> dict:
    """Parse the LLM-generated outreach block into ``{llm_subject, llm_body}``.

    Robust against:
      - markdown leftovers (```text``` fences)
      - extra blank lines
      - the LLM omitting one of the labels (free text becomes the body)
    """
    cleaned = text.strip()
    # Strip markdown code fences if present.
    cleaned = re.sub(r"^```[^\n]*\n", "", cleaned)
    cleaned = re.sub(r"\n```$", "", cleaned)

    fields: dict[str, str] = {}
    # Multi-line content under each label: scan greedily until next label
    # or end of text.
    matches = list(_FIELD_RE.finditer(cleaned))
    for i, m in enumerate(matches):
        label = m.group(1).lower()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cleaned)
        value = cleaned[m.end() : end].strip()
        # Single-line BETREFF: take only first line.
        if label in ("betreff", "subject"):
            value = value.splitlines()[0].strip() if value else ""
            fields["llm_subject"] = value
        else:
            fields["llm_body"] = value

    if not fields:
        # Fallback: no labels found → treat whole text as body, no subject.
        return {
            "llm_subject": "",
            "llm_body": cleaned,
            "_unparsed": True,
        }
    if "llm_subject" not in fields:
        fields["llm_subject"] = ""
    if "llm_body" not in fields:
        fields["llm_body"] = ""
    return fields


# ─────────────────────────────────────────────────────────────────────
# Single-enrollment generation
# ─────────────────────────────────────────────────────────────────────


async def generate_for_enrollment(
    db: AsyncSession,
    tenant_id: str,
    tenant_config: dict,
    enrollment: PipelineEnrollment,
    pipeline: EngagementPipeline,
    prompt: PipelinePrompt,
    model_override: str | None = None,
) -> tuple[dict, dict]:
    """Run the LLM once for the given enrollment + prompt.

    Returns ``(parsed_fields, usage_dict)`` where parsed_fields is
    ``{llm_subject, llm_body, ...}`` and usage_dict is the Anthropic
    token usage (cache_read/cache_create/input/output).
    """
    ctx = await get_contact_context(db, tenant_id, enrollment.contact_id)
    variables = _build_outreach_variables(ctx)

    cached_system, dynamic_block = _split_prompt_for_caching(
        prompt.system_prompt, variables
    )

    model = model_override or prompt.model or get_default_model("standard")
    llm = LLMService(tenant_config=tenant_config)

    started = time.perf_counter()
    if cached_system is not None:
        text, usage = await llm.generate_with_cached_system(
            model=model,
            system_prompt=cached_system,
            user_prompt=dynamic_block,
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
    else:
        from app.engagement.prompts_router import _fill_placeholders

        system_filled = _fill_placeholders(prompt.system_prompt, variables)
        text = await llm.generate_with_config(
            provider="anthropic",
            model=model,
            system_prompt=system_filled,
            user_prompt="Bitte erzeuge den Text gemäß den Vorgaben.",
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        )
        usage = {}

    fields = parse_brain_output(text)
    fields["_raw"] = text
    fields["_model"] = model
    fields["_duration_ms"] = int((time.perf_counter() - started) * 1000)
    return fields, usage


# ─────────────────────────────────────────────────────────────────────
# Bulk runner
# ─────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def _resolve_prompt(
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: int,
    channel: str,
    slot: str,
) -> PipelinePrompt:
    """Find the prompt for (pipeline, channel, slot). Falls back to
    'initial' if the requested slot doesn't exist."""
    stmt = select(PipelinePrompt).where(
        and_(
            PipelinePrompt.tenant_id == tenant_id,
            PipelinePrompt.pipeline_id == pipeline_id,
            PipelinePrompt.channel == channel,
            PipelinePrompt.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    if not rows:
        raise NotFoundError("PipelinePrompt", f"pipeline={pipeline_id} channel={channel}")
    by_slot = {p.slot: p for p in rows}
    if slot in by_slot:
        return by_slot[slot]
    if "initial" in by_slot:
        return by_slot["initial"]
    return rows[0]


async def _enrollments_needing_draft(
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: int,
    channel: str,
    limit: int | None = None,
) -> list[PipelineEnrollment]:
    """Pick enrollments that don't yet have a pending email-action in
    ready_for_approval/approved state.

    We re-generate for cancelled/failed actions but skip ones already
    queued or sent.
    """
    stmt = (
        select(PipelineEnrollment)
        .where(
            PipelineEnrollment.tenant_id == tenant_id,
            PipelineEnrollment.pipeline_id == pipeline_id,
            PipelineEnrollment.status == "active",
        )
        .order_by(PipelineEnrollment.id)
    )
    if limit:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    enrollments = list(result.scalars().all())

    # Filter out enrollments that already have an active email pending action
    if not enrollments:
        return []
    enrollment_ids = [e.id for e in enrollments]
    existing_q = select(PendingAction.enrollment_id).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.pipeline_id == pipeline_id,
        PendingAction.module == channel,
        PendingAction.enrollment_id.in_(enrollment_ids),
        PendingAction.status.in_(["ready_for_approval", "approved", "completed"]),
    )
    existing = (await db.execute(existing_q)).scalars().all()
    existing_set = set(existing)
    candidates = [e for e in enrollments if e.id not in existing_set]

    # Wenn channel = email: Empfänger die abgemeldet sind, gar nicht erst
    # mit LLM-Tokens für Drafts belasten. Spart Kosten + sauberer Audit-Trail.
    if channel == "email" and candidates:
        from app.emailmarketing.models import EmailUnsubscribe
        suppressed = {
            row[0].lower()
            for row in (await db.execute(
                select(EmailUnsubscribe.email).where(
                    EmailUnsubscribe.tenant_id == tenant_id
                )
            )).all()
        }
        if suppressed:
            contact_ids = [e.contact_id for e in candidates]
            email_rows = (await db.execute(
                select(Contact.id, Contact.email).where(Contact.id.in_(contact_ids))
            )).all()
            unsubscribed_contact_ids = {
                cid for cid, email in email_rows
                if email and email.lower() in suppressed
            }
            if unsubscribed_contact_ids:
                logger.info(
                    "Brain-Bulk-Run: {n} Enrollments übersprungen (abgemeldet)",
                    n=len(unsubscribed_contact_ids),
                )
                candidates = [
                    e for e in candidates
                    if e.contact_id not in unsubscribed_contact_ids
                ]
    return candidates


async def run_bulk_brain(
    db: AsyncSession,
    tenant_id: str,
    tenant_config: dict,
    pipeline_id: int,
    channel: str,
    slot: str,
    limit: int | None = None,
    model_override: str | None = None,
    progress_callback=None,
) -> dict:
    """Generate drafts for all enrollments in the pipeline that don't
    already have one. Writes pending_actions, updates pipeline.bulk_brain_status.

    Returns a summary dict.
    """
    # Load pipeline
    pipeline = (
        await db.execute(
            select(EngagementPipeline).where(
                EngagementPipeline.id == pipeline_id,
                EngagementPipeline.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not pipeline:
        raise NotFoundError("Pipeline", pipeline_id)

    prompt = await _resolve_prompt(db, tenant_id, pipeline_id, channel, slot)
    enrollments = await _enrollments_needing_draft(
        db, tenant_id, pipeline_id, channel, limit
    )
    if not enrollments:
        raise ValidationError(
            "Keine Enrollments ohne offenen Draft gefunden — alle haben "
            "bereits eine Email-Action im Freigabe-Tab."
        )

    auto_actions = pipeline.auto_actions or {}
    auto_send = bool(auto_actions.get(f"{channel}_send", False))

    # Customer-Journey-Verknüpfung einmal pro Pipeline einrichten — der
    # Per-Enrollment-Loop unten hängt dann nur noch die Ref-Codes an.
    # Idempotent: wenn schon verheiratet, nutzt nur einen SELECT.
    journey_campaign = await CampaignService(db).ensure_for_pipeline(pipeline)
    ref_service = RefCodeService(db)
    utm_cfg = (pipeline.tracking_config or {}).get("utm") or {}
    ref_target_url = (pipeline.tracking_config or {}).get("base_url")

    total = len(enrollments)
    status = {
        "channel": channel,
        "slot": slot,
        "model": model_override or prompt.model or get_default_model("standard"),
        "total": total,
        "done": 0,
        "errors": [],
        "cache_read_total": 0,
        "cache_create_total": 0,
        "input_total": 0,
        "output_total": 0,
        "started_at": _now_iso(),
        "finished_at": None,
        "status": "running",
    }
    pipeline.bulk_brain_status = dict(status)
    await db.commit()

    for enrollment in enrollments:
        try:
            # Pre-generate the Customer-Journey ref-code for this recipient
            # so the Drafts-Manager can show the final tracking link without
            # a render-time DB write. Idempotent if it already exists.
            contact = (
                await db.execute(
                    select(Contact).where(Contact.id == enrollment.contact_id)
                )
            ).scalar_one_or_none()
            if contact is not None:
                ref = await ref_service.ensure_ref_code(
                    tenant_id=tenant_id,
                    contact=contact,
                    campaign=journey_campaign,
                    target_url=ref_target_url,
                    utm_source=utm_cfg.get("source", "outreach"),
                    utm_medium=utm_cfg.get("medium", channel),
                    utm_campaign=utm_cfg.get("campaign", pipeline.slug),
                )
                if enrollment.journey_ref_code_id != ref.id:
                    enrollment.journey_ref_code_id = ref.id

            fields, usage = await generate_for_enrollment(
                db=db,
                tenant_id=tenant_id,
                tenant_config=tenant_config,
                enrollment=enrollment,
                pipeline=pipeline,
                prompt=prompt,
                model_override=model_override,
            )
            content_payload = {
                "llm_subject": fields.get("llm_subject", ""),
                "llm_body": fields.get("llm_body", ""),
                "_raw": fields.get("_raw", ""),
                "_model": fields.get("_model", ""),
                "_prompt_id": prompt.id,
                "_slot": slot,
            }
            action = PendingAction(
                tenant_id=tenant_id,
                contact_id=enrollment.contact_id,
                pipeline_id=pipeline_id,
                enrollment_id=enrollment.id,
                module=channel,
                action_type=f"{channel}_send",
                context={
                    "template_id": None,
                    "slot": slot,
                    "prompt_id": prompt.id,
                    "model_used": content_payload["_model"],
                    "duration_ms": fields.get("_duration_ms", 0),
                    "generated_at": _now_iso(),
                    "_unparsed": fields.get("_unparsed", False),
                },
                suggested_content=json.dumps(content_payload, ensure_ascii=False),
                priority="normal",
                needs_approval=not auto_send,
                status="approved" if auto_send else "ready_for_approval",
            )
            db.add(action)
            await db.flush()
            status["done"] += 1
            status["cache_read_total"] += int(
                usage.get("cache_read_input_tokens", 0)
            )
            status["cache_create_total"] += int(
                usage.get("cache_creation_input_tokens", 0)
            )
            status["input_total"] += int(usage.get("input_tokens", 0))
            status["output_total"] += int(usage.get("output_tokens", 0))
        except Exception as exc:
            logger.exception(
                "Bulk-Brain failed for enrollment {eid}", eid=enrollment.id
            )
            status["errors"].append(
                {"enrollment_id": enrollment.id, "error": str(exc)[:300]}
            )
        # Persist progress every 5 records (or on the last one) so the UI
        # can poll without too much DB churn.
        if status["done"] % 5 == 0 or status["done"] == total:
            pipeline.bulk_brain_status = dict(status)
            await db.commit()
        if progress_callback:
            progress_callback(status)

        # Cancel-Check: re-read the persisted status after each commit. If
        # someone called the stop endpoint (sets status='cancel_requested'),
        # we exit cleanly — bisherige Drafts bleiben in der DB.
        if status["done"] % 5 == 0:
            await db.refresh(pipeline, ["bulk_brain_status"])
            persisted = pipeline.bulk_brain_status or {}
            if persisted.get("status") == "cancel_requested":
                logger.info(
                    "Bulk-Brain cancelled by user at {done}/{total}",
                    done=status["done"], total=total,
                )
                status["status"] = "cancelled"
                status["finished_at"] = _now_iso()
                pipeline.bulk_brain_status = dict(status)
                await db.commit()
                return status

    status["status"] = "done"
    status["finished_at"] = _now_iso()
    pipeline.bulk_brain_status = dict(status)
    await db.commit()
    logger.info(
        "Bulk-Brain done: pipeline={pid} channel={ch} slot={s} "
        "done={d}/{t} cache_read={cr} cache_create={cc}",
        pid=pipeline_id,
        ch=channel,
        s=slot,
        d=status["done"],
        t=total,
        cr=status["cache_read_total"],
        cc=status["cache_create_total"],
    )
    return status


# ─────────────────────────────────────────────────────────────────────
# Mass operations on existing drafts
# ─────────────────────────────────────────────────────────────────────


async def regenerate_action(
    db: AsyncSession,
    tenant_id: str,
    tenant_config: dict,
    action: PendingAction,
    model_override: str | None = None,
) -> dict:
    """Re-run the LLM for a single existing pending_action and overwrite
    its suggested_content. Useful when the user wants to retry a draft
    they didn't like."""
    enrollment_q = await db.execute(
        select(PipelineEnrollment).where(
            PipelineEnrollment.id == action.enrollment_id
        )
    )
    enrollment = enrollment_q.scalar_one_or_none()
    if not enrollment:
        raise NotFoundError("Enrollment", action.enrollment_id)
    pipeline_q = await db.execute(
        select(EngagementPipeline).where(EngagementPipeline.id == action.pipeline_id)
    )
    pipeline = pipeline_q.scalar_one_or_none()
    if not pipeline:
        raise NotFoundError("Pipeline", action.pipeline_id)

    slot = (action.context or {}).get("slot", "initial")
    prompt = await _resolve_prompt(
        db, tenant_id, action.pipeline_id, action.module, slot
    )
    fields, usage = await generate_for_enrollment(
        db=db,
        tenant_id=tenant_id,
        tenant_config=tenant_config,
        enrollment=enrollment,
        pipeline=pipeline,
        prompt=prompt,
        model_override=model_override,
    )
    content_payload = {
        "llm_subject": fields.get("llm_subject", ""),
        "llm_body": fields.get("llm_body", ""),
        "_raw": fields.get("_raw", ""),
        "_model": fields.get("_model", ""),
        "_prompt_id": prompt.id,
        "_slot": slot,
    }
    action.suggested_content = json.dumps(content_payload, ensure_ascii=False)
    new_ctx = dict(action.context or {})
    new_ctx["model_used"] = content_payload["_model"]
    new_ctx["duration_ms"] = fields.get("_duration_ms", 0)
    new_ctx["regenerated_at"] = _now_iso()
    new_ctx["_unparsed"] = fields.get("_unparsed", False)
    action.context = new_ctx
    await db.commit()
    return {"action_id": action.id, "fields": content_payload, "usage": usage}


async def mass_replace_in_drafts(
    db: AsyncSession,
    tenant_id: str,
    pipeline_id: int,
    find: str,
    replace: str,
    fields: list[str] | None = None,
) -> dict:
    """Apply a literal text replacement over all ready_for_approval
    email drafts in the pipeline. Returns a count summary.
    """
    if not find:
        raise ValidationError("'find' darf nicht leer sein.")
    if fields is None:
        fields = ["llm_subject", "llm_body"]

    stmt = select(PendingAction).where(
        PendingAction.tenant_id == tenant_id,
        PendingAction.pipeline_id == pipeline_id,
        PendingAction.module == "email",
        PendingAction.status == "ready_for_approval",
    )
    result = await db.execute(stmt)
    actions = list(result.scalars().all())
    changed = 0
    for action in actions:
        try:
            payload: Any = json.loads(action.suggested_content or "{}")
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        any_change = False
        for f in fields:
            v = payload.get(f, "")
            if isinstance(v, str) and find in v:
                payload[f] = v.replace(find, replace)
                any_change = True
        if any_change:
            action.suggested_content = json.dumps(payload, ensure_ascii=False)
            changed += 1
    if changed:
        await db.commit()
    return {"matched": len(actions), "changed": changed}
