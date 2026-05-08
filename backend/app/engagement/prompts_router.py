"""Per-pipeline channel-specific prompt CRUD + test endpoints.

Mounted under /v1/engagement/pipelines/{pipeline_id}/prompts
"""

import re
import time

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.context_loader import get_contact_context
from app.database import get_db
from app.engagement.models import EngagementPipeline, PipelinePrompt
from app.engagement.schemas import (
    PipelinePromptCreate,
    PipelinePromptResponse,
    PipelinePromptTestRequest,
    PipelinePromptTestResponse,
    PipelinePromptUpdate,
)
from app.exceptions import NotFoundError
from app.services.llm import DEFAULT_MODELS, LLMService, get_default_model
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(
    prefix="/engagement/pipelines/{pipeline_id}/prompts",
    tags=["engagement-prompts"],
)


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _fill_placeholders(text: str, variables: dict) -> str:
    """Replace {{name}} with str(variables[name]) — missing keys -> empty."""
    def sub(match: re.Match) -> str:
        key = match.group(1)
        val = variables.get(key, "")
        return str(val) if val is not None else ""
    return _PLACEHOLDER_RE.sub(sub, text)


def _derive_empowerment_profile(services: list, hook: str | None) -> str:
    """Heuristic: wallbox_erfahren / elektriker_neu_im_segment / unklar.

    Looks at the services list and the personalization_hook for direct
    e-mobility / wallbox / Ladeinfrastruktur references.
    """
    text_blob = " ".join(services or []).lower()
    if hook:
        text_blob += " " + hook.lower()
    wallbox_signals = (
        "wallbox", "ladeinfrastruktur", "ladestation", "ladesäule",
        "ladesaeule", "ladepunkt", "e-mobilität", "e-mobilitaet",
        "elektromobilität", "elektromobilitaet", "ladesystem",
    )
    elektriker_signals = ("elektroinstallation", "elektrotechnik", "elektriker")
    has_wallbox = any(s in text_blob for s in wallbox_signals)
    has_elektriker = any(s in text_blob for s in elektriker_signals)
    if has_wallbox:
        return "wallbox_erfahren"
    if has_elektriker:
        return "elektriker_neu_im_segment"
    return "unklar"


def _derive_mfh_affinity(customer_segments: list, hook: str | None) -> str:
    """Heuristic: hoch / mittel / niedrig / unklar based on customer segments.

    Looks for explicit MFH/WEG/Hausverwaltung mentions; falls back to
    Gewerbe/Industrie (mittel) and EFH/Privat-only (niedrig).
    """
    seg_text = " ".join(customer_segments or []).lower()
    hook_text = (hook or "").lower()
    blob = seg_text + " " + hook_text
    high_signals = (
        "mfh", "mehrfamilienhaus", "mehrfamilienhäuser",
        "mehrfamilienhaeuser", "weg", "wohnungseigentümer",
        "wohnungseigentuemer", "hausverwaltung", "wohnanlage",
        "wohnungsbau", "immobilienverwaltung",
    )
    mid_signals = ("gewerbe", "industrie", "öffentliche", "oeffentliche")
    if any(s in blob for s in high_signals):
        return "hoch"
    has_mid = any(s in seg_text for s in mid_signals)
    has_efh = "efh" in seg_text or "privat" in seg_text or "einfamilien" in seg_text
    if has_mid:
        return "mittel"
    if has_efh:
        return "niedrig"
    return "unklar"


def _build_pre_pitch_bullets(ctx: dict) -> str:
    """Combine personalization_hook + services + segments + size into a
    bullet-list ready for the prompt.

    Falls back to whatever pieces exist; returns an empty string if nothing
    useful is available.
    """
    parts: list[str] = []
    hook = (ctx.get("personalization_hook") or "").strip()
    if hook:
        # Already comes as a multi-line bullet list from the leadgen LLM.
        parts.append(hook)
    services = ctx.get("services") or []
    if services:
        parts.append("- Dienstleistungen: " + ", ".join(services))
    segments = ctx.get("customer_segments") or []
    if segments:
        parts.append("- Kundensegmente: " + ", ".join(segments))
    size = (ctx.get("company_size_indicator") or "").strip()
    if size:
        parts.append("- Firmengröße: " + size)
    brands = ctx.get("brands") or []
    if brands:
        parts.append("- Marken/Hersteller: " + ", ".join(brands))
    google_cats = ctx.get("google_categories") or []
    if google_cats and not services:
        parts.append("- Branchen-Kategorien: " + ", ".join(google_cats))
    return "\n".join(parts)


def _build_outreach_variables(ctx: dict) -> dict:
    """Map a contact context into the placeholder variables that outreach
    prompts typically expect. Includes derived fields (empowerment profile,
    MFH affinity, pre-pitch bullets) on top of the raw context keys."""
    full_name = (ctx.get("name") or "").strip()
    parts = full_name.split()
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""
    primary = ctx.get("primary_contact") or {}
    salutation = primary.get("salutation") or ctx.get("salutation") or "Herr/Frau"
    services = ctx.get("services") or []
    customer_segments = ctx.get("customer_segments") or []
    hook = ctx.get("personalization_hook")
    return {
        # Basic contact + company
        "firmenname": ctx.get("company_name") or "",
        "ort": ctx.get("address_city") or ctx.get("city") or "",
        "anrede_gf": salutation,
        "name_gf": full_name,
        "first_name": primary.get("first_name") or first,
        "last_name": primary.get("last_name") or last,
        "position": ctx.get("position") or primary.get("role") or "",
        # Rich leadgen context
        "homepage_zusammenfassung": _build_pre_pitch_bullets(ctx),
        "pre_pitch_bullets": _build_pre_pitch_bullets(ctx),
        "personalization_hook": hook or "",
        "services": ", ".join(services),
        "customer_segments": ", ".join(customer_segments),
        "company_size_indicator": ctx.get("company_size_indicator") or "",
        "target_match_score": ctx.get("target_match_score") or "",
        # Derived heuristics for prompt branching
        "empowerment_profil": _derive_empowerment_profile(services, hook),
        "mfh_affinitaet": _derive_mfh_affinity(customer_segments, hook),
    }


async def _ensure_pipeline(
    db: AsyncSession, tenant_id: str, pipeline_id: int
) -> EngagementPipeline:
    """Load pipeline scoped to tenant — 404 if not found."""
    stmt = select(EngagementPipeline).where(
        EngagementPipeline.id == pipeline_id,
        EngagementPipeline.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise NotFoundError("Pipeline", pipeline_id)
    return pipeline


@router.get("", response_model=list[PipelinePromptResponse])
async def list_prompts(
    pipeline_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[PipelinePromptResponse]:
    """List all prompts for a pipeline, ordered by channel + sort_order."""
    await _ensure_pipeline(db, tenant_id, pipeline_id)
    stmt = (
        select(PipelinePrompt)
        .where(
            PipelinePrompt.tenant_id == tenant_id,
            PipelinePrompt.pipeline_id == pipeline_id,
        )
        .order_by(
            PipelinePrompt.channel,
            PipelinePrompt.sort_order,
            PipelinePrompt.id,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "",
    response_model=PipelinePromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    pipeline_id: int,
    data: PipelinePromptCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelinePromptResponse:
    """Create a new prompt for a pipeline-channel slot."""
    await _ensure_pipeline(db, tenant_id, pipeline_id)
    prompt = PipelinePrompt(
        tenant_id=tenant_id,
        pipeline_id=pipeline_id,
        **data.model_dump(),
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    await db.commit()
    logger.info(
        "PipelinePrompt created: pipeline={pid} channel={ch} slot={slot}",
        pid=pipeline_id,
        ch=data.channel,
        slot=data.slot,
    )
    return prompt


@router.put("/{prompt_id}", response_model=PipelinePromptResponse)
async def update_prompt(
    pipeline_id: int,
    prompt_id: int,
    data: PipelinePromptUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PipelinePromptResponse:
    """Update a prompt."""
    await _ensure_pipeline(db, tenant_id, pipeline_id)
    stmt = select(PipelinePrompt).where(
        PipelinePrompt.id == prompt_id,
        PipelinePrompt.pipeline_id == pipeline_id,
        PipelinePrompt.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt nicht gefunden")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(prompt, key, val)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_prompt(
    pipeline_id: int,
    prompt_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a prompt."""
    stmt = select(PipelinePrompt).where(
        PipelinePrompt.id == prompt_id,
        PipelinePrompt.pipeline_id == pipeline_id,
        PipelinePrompt.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt nicht gefunden")
    await db.delete(prompt)
    await db.commit()


@router.post("/{prompt_id}/test", response_model=PipelinePromptTestResponse)
async def test_prompt(
    pipeline_id: int,
    prompt_id: int,
    data: PipelinePromptTestRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> PipelinePromptTestResponse:
    """Run the prompt with the given variables (or auto-resolved from a
    contact_id) and return the LLM output. Does NOT send anything anywhere."""
    await _ensure_pipeline(db, tenant_id, pipeline_id)
    stmt = select(PipelinePrompt).where(
        PipelinePrompt.id == prompt_id,
        PipelinePrompt.pipeline_id == pipeline_id,
        PipelinePrompt.tenant_id == tenant_id,
    )
    result = await db.execute(stmt)
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt nicht gefunden")

    # Build variables: explicit > resolved-from-contact
    variables: dict = {}
    if data.contact_id:
        try:
            ctx = await get_contact_context(db, tenant_id, data.contact_id)
            variables.update(_build_outreach_variables(ctx))
        except Exception as exc:
            logger.warning(
                "Context-loader failed for contact {cid}: {err}",
                cid=data.contact_id,
                err=str(exc),
            )
    # Explicit variables override
    variables.update(data.variables or {})

    # Standard-Klasse als Default-Modell wenn der Prompt keines setzt.
    model = prompt.model or get_default_model("standard")
    if model not in DEFAULT_MODELS.values() and not model.startswith("claude"):
        # Be permissive — user might pin a specific model
        pass

    # Auto-split: cache the static prefix (everything before the first
    # variable) and pass the variable values as a fresh user message. This
    # cuts ~90 % of input cost on bulk runs (1000 contacts sharing one
    # prompt). Falls back to plain mode if the prompt is too short.
    cached_system, dynamic_block = _split_prompt_for_caching(
        prompt.system_prompt, variables
    )

    llm = LLMService(tenant_config=tenant_config)
    started = time.perf_counter()
    try:
        if cached_system is not None:
            text, usage = await llm.generate_with_cached_system(
                model=model,
                system_prompt=cached_system,
                user_prompt=dynamic_block,
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
            )
        else:
            # Short prompt or no variables — no caching benefit.
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
    except Exception as exc:
        logger.exception("LLM-Aufruf für Prompt-Test fehlgeschlagen")
        raise HTTPException(
            status_code=502,
            detail=f"LLM-Fehler: {exc}",
        ) from exc
    duration_ms = int((time.perf_counter() - started) * 1000)

    return PipelinePromptTestResponse(
        output=text,
        model_used=model,
        duration_ms=duration_ms,
        cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_tokens=usage.get("cache_read_input_tokens", 0),
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
    )


def _split_prompt_for_caching(
    system_prompt: str, variables: dict
) -> tuple[str | None, str]:
    """Prepare a templated prompt for Anthropic ephemeral caching.

    Strategy:
      - The full system prompt (with ``{{placeholders}}`` left untouched)
        becomes the cached block. It is byte-identical across all calls
        for the same prompt-row, so the cache hits cleanly.
      - The dynamic user message provides the resolved variable values as
        a key-value list. The model understands implicitly that the
        placeholders in the system prompt should be substituted from the
        values listed in the user message.

    Returns ``(cached_system, user_message)`` or ``(None, "")`` when the
    prompt is too short to benefit from caching (< ~1024 tokens) or
    contains no placeholders.
    """
    placeholders = list(_PLACEHOLDER_RE.finditer(system_prompt))
    if not placeholders:
        return None, ""

    # Anthropic ephemeral cache requires >= 1024 tokens. Heuristic:
    # ~4 chars per token → 4096 chars threshold.
    if len(system_prompt) < 4096:
        return None, ""

    used_keys: list[str] = []
    for m in placeholders:
        if m.group(1) not in used_keys:
            used_keys.append(m.group(1))

    lines = [
        "Hier sind die konkreten Werte für die Platzhalter im System-Prompt:",
        "",
    ]
    for key in used_keys:
        val = variables.get(key, "")
        if val is None:
            val = ""
        # Multi-line values render cleaner with a header + indented body.
        if "\n" in str(val):
            lines.append(f"{{{{{key}}}}}:")
            for sub in str(val).splitlines():
                lines.append(f"  {sub}")
        else:
            lines.append(f"{{{{{key}}}}}: {val}")
    lines.append("")
    lines.append(
        "Setze diese Werte in den System-Prompt ein und erzeuge die Ausgabe "
        "gemäß den Vorgaben. Keine Erklärungen, keine Meta-Kommentare."
    )
    return system_prompt, "\n".join(lines)
