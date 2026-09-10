"""triage — claude-haiku-4-5 classifies the raw diff.

Uses Anthropic tool-use with a strict ``classify_change`` schema so we
always get back ``{change_type, significance}`` as JSON.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.intel.models import IntelChangeEvent, IntelSnapshot, IntelSource

_HAIKU = "claude-haiku-4-5-20251001"

_CLASSIFY_TOOL = {
    "name": "classify_change",
    "description": (
        "Classify the observed change between two snapshots of the same "
        "competitor/regulator/market source. Return a single decision."
    ),
    "input_schema": {
        "type": "object",
        "required": ["change_type", "significance"],
        "additionalProperties": False,
        "properties": {
            "change_type": {
                "type": "string",
                "description": (
                    "Short slug: price_change | product_launch | "
                    "personnel_change | hiring_signal | partnership | "
                    "regulation_update | content_refresh | other"
                ),
                "minLength": 1,
                "maxLength": 50,
            },
            "significance": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "0 = trivial/cosmetic, 0.5 = moderate, 1 = high-impact "
                    "for competitive intelligence."
                ),
            },
        },
    },
}


async def triage(
    db: AsyncSession,
    event: IntelChangeEvent,
    *,
    client_factory=None,
) -> None:
    """Set ``change_type`` and ``significance`` on the event in-place.

    If ``significance < settings.intel_triage_threshold``, marks
    ``processed_at`` so ``reason()`` skips the event.

    ``client_factory`` is a hook for tests — default uses Anthropic.
    """
    snap = await db.get(IntelSnapshot, event.new_snapshot_id)
    source = await db.get(IntelSource, event.source_id) if snap else None
    if snap is None or source is None:
        logger.warning("triage: missing snapshot/source for event {eid}", eid=event.id)
        event.processed_at = datetime.utcnow()
        await db.flush()
        return

    prompt = _build_prompt(event, snap, source)
    client_factory = client_factory or _default_anthropic_factory

    try:
        decision = await asyncio.wait_for(
            _call(client_factory, prompt),
            timeout=settings.intel_llm_timeout_sec,
        )
    except TimeoutError:
        logger.warning("triage timeout for event {eid}", eid=event.id)
        return
    except Exception as e:
        logger.exception("triage LLM error for event {eid}: {e}", eid=event.id, e=str(e))
        return

    event.change_type = decision["change_type"][:50]
    event.significance = Decimal(str(decision["significance"]))

    if float(event.significance) < settings.intel_triage_threshold:
        event.processed_at = datetime.utcnow()
        logger.debug(
            "triage: event {eid} below threshold ({sig}); skipped",
            eid=event.id,
            sig=event.significance,
        )
    await db.flush()


# ── helpers ──────────────────────────────────────────────────────────


def _build_prompt(
    event: IntelChangeEvent, snap: IntelSnapshot, source: IntelSource
) -> str:
    diff_lines = (event.raw_diff or {}).get("text_diff", []) or []
    diff_text = "\n".join(diff_lines[:120])
    parsed_diff = (event.raw_diff or {}).get("parsed_diff", {}) or {}
    return (
        f"Source URL: {snap.source_url or '?'}\n"
        f"Adapter: {source.adapter}\n"
        f"Parsed structural diff: {parsed_diff}\n\n"
        f"Unified text diff (truncated):\n{diff_text}\n"
    )


def _default_anthropic_factory():
    """Build an AsyncAnthropic client from settings."""
    from anthropic import AsyncAnthropic  # local import keeps cold-paths slim

    return AsyncAnthropic(api_key=settings.anthropic_api_key)


async def _call(client_factory, prompt: str) -> dict:
    """Invoke the model with tool_choice forced on classify_change."""
    client = client_factory()
    response = await client.messages.create(
        model=_HAIKU,
        max_tokens=400,
        tools=[_CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_change"},
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a B2B competitive-intelligence analyst. "
                    "Classify the change below. Return ONE tool call to "
                    "classify_change.\n\n" + prompt
                ),
            }
        ],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "classify_change":
            return dict(block.input)
    raise RuntimeError("triage: model did not call classify_change")
