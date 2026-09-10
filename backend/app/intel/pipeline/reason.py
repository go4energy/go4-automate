"""reason — claude-sonnet-4-6 generates headline + summary + impact.

JSON-mode output. Every claim must be tied to an evidence URL — we
seed the model with the source URL and require it to echo it back.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intel.models import (
    IntelChangeEvent,
    IntelSnapshot,
    IntelSource,
    IntelWatchTarget,
)
from app.intel.schemas import ReasonOutput

_SONNET = "claude-sonnet-4-6"


async def reason(
    db: AsyncSession,
    event: IntelChangeEvent,
    *,
    client_factory=None,
) -> None:
    """Populate headline/summary/impact_assessment/evidence.

    Sets ``processed_at`` once done. Re-runs are no-ops.
    """
    if event.processed_at is not None:
        return

    snap = await db.get(IntelSnapshot, event.new_snapshot_id)
    source = await db.get(IntelSource, event.source_id) if snap else None
    target = (
        await db.get(IntelWatchTarget, source.target_id)
        if source is not None
        else None
    )
    if snap is None or source is None or target is None:
        logger.warning("reason: missing context for event {eid}", eid=event.id)
        event.processed_at = datetime.utcnow()
        await db.flush()
        return

    prompt = _build_prompt(event, snap, source, target)
    client_factory = client_factory or _default_anthropic_factory

    try:
        parsed = await asyncio.wait_for(
            _call(client_factory, prompt, retries=1),
            timeout=settings.intel_llm_timeout_sec,
        )
    except TimeoutError:
        logger.warning("reason timeout for event {eid}", eid=event.id)
        return
    except Exception as e:
        logger.exception("reason LLM error for event {eid}: {e}", eid=event.id, e=str(e))
        return

    # Ensure source URL is in evidence
    evidence = list(parsed.evidence)
    src_url = snap.source_url
    if src_url and not any(e.get("url") == src_url for e in evidence):
        evidence.append({"url": src_url, "fetched_at": snap.fetched_at.isoformat()})

    event.headline = parsed.headline[:500]
    event.summary = parsed.summary
    event.impact_assessment = parsed.impact_assessment
    event.evidence = evidence
    event.processed_at = datetime.utcnow()
    await db.flush()


# ── helpers ──────────────────────────────────────────────────────────


def _build_prompt(
    event: IntelChangeEvent,
    snap: IntelSnapshot,
    source: IntelSource,
    target: IntelWatchTarget,
) -> str:
    diff_lines = (event.raw_diff or {}).get("text_diff", []) or []
    diff_text = "\n".join(diff_lines[:200])
    ctx = target.context or {}
    return (
        f"Watch-Target: {target.name} (kind={target.kind})\n"
        f"Context: {json.dumps(ctx, ensure_ascii=False)}\n"
        f"Change Type (from triage): {event.change_type}\n"
        f"Significance: {event.significance}\n"
        f"Source URL: {snap.source_url or '?'}\n\n"
        f"Diff:\n{diff_text}\n"
    )


def _default_anthropic_factory():
    from anthropic import AsyncAnthropic

    return AsyncAnthropic(api_key=settings.anthropic_api_key)


_SYSTEM = (
    "You are a B2B competitive-intelligence analyst writing for a German "
    "marketing-automation platform. Respond ONLY with strict JSON matching "
    'this schema: {"headline": str, "summary": str, '
    '"impact_assessment": str, "evidence": [{"url": str, "fetched_at": '
    'str}]}. No prose outside JSON. The evidence array MUST include the '
    "source URL. Keep summary ≤ 5 sentences. Write in German."
)


async def _call(client_factory, prompt: str, *, retries: int) -> ReasonOutput:
    """Single attempt, retry once on JSONDecodeError."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        client = client_factory()
        response = await client.messages.create(
            model=_SONNET,
            max_tokens=1200,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        try:
            data = json.loads(text)
            return ReasonOutput.model_validate(data)
        except Exception as e:
            last_err = e
            logger.debug(
                "reason: JSON parse attempt {a} failed: {e}", a=attempt, e=str(e)
            )
            continue
    raise RuntimeError(f"reason: model did not return valid JSON: {last_err}")
