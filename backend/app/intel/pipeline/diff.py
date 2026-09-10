"""detect_change — compare two snapshots, create ChangeEvent if meaningful.

Layered cheap-to-expensive checks:
1. ``content_hash`` equality   → no change
2. Text similarity (difflib)   → if ≥ 0.95, treat as trivial (whitespace, dates)
3. Embedding cosine distance   → if < 0.05, semantic-trivial → drop
4. Otherwise build a ChangeEvent with raw_diff for downstream triage.
"""

from __future__ import annotations

import difflib
import math
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intel.models import IntelChangeEvent, IntelSnapshot

# Tunable thresholds — kept as module-level so tests can monkey-patch.
TEXT_SIMILARITY_TRIVIAL = 0.95
COSINE_DISTANCE_TRIVIAL = 0.05
TEXT_DIFF_MAX_LINES = 200


async def detect_change(
    db: AsyncSession, new_snap: IntelSnapshot
) -> IntelChangeEvent | None:
    """Compare new_snap to the previous snapshot for same source.

    Returns the persisted ChangeEvent or ``None`` if no meaningful
    change was detected (or this is the first snapshot for the source).
    """
    prev = await _previous_snapshot(db, new_snap)
    if prev is None:
        logger.debug("First snapshot for source {sid} — no diff", sid=new_snap.source_id)
        return None

    if prev.content_hash == new_snap.content_hash:
        return None

    text_ratio = _text_similarity(prev.text, new_snap.text)
    if text_ratio >= TEXT_SIMILARITY_TRIVIAL:
        logger.debug(
            "Trivial text-only change for source {sid} (ratio={r:.3f})",
            sid=new_snap.source_id,
            r=text_ratio,
        )
        return None

    cosine = _cosine_distance(prev.embedding, new_snap.embedding)
    if cosine is not None and cosine < COSINE_DISTANCE_TRIVIAL:
        logger.debug(
            "Semantically trivial change for source {sid} (cosine={c:.3f})",
            sid=new_snap.source_id,
            c=cosine,
        )
        return None

    event = IntelChangeEvent(
        tenant_id=new_snap.tenant_id,
        source_id=new_snap.source_id,
        prev_snapshot_id=prev.id,
        new_snapshot_id=new_snap.id,
        change_type="unclassified",
        significance=Decimal("0.50"),
        raw_diff={
            "text_diff": _unified_diff(prev.text, new_snap.text),
            "text_similarity": round(text_ratio, 4),
            "cosine_distance": (
                round(cosine, 4) if cosine is not None else None
            ),
            "parsed_diff": _parsed_diff(prev.parsed, new_snap.parsed),
        },
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    logger.info(
        "Change detected for source {sid}: event {eid}",
        sid=new_snap.source_id,
        eid=event.id,
    )
    return event


# ── internal helpers ─────────────────────────────────────────────────


async def _previous_snapshot(
    db: AsyncSession, new_snap: IntelSnapshot
) -> IntelSnapshot | None:
    """Return the most-recent snapshot for this source preceding new_snap."""
    result = await db.execute(
        select(IntelSnapshot)
        .where(
            IntelSnapshot.source_id == new_snap.source_id,
            IntelSnapshot.id != new_snap.id,
        )
        .order_by(IntelSnapshot.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _text_similarity(a: str, b: str) -> float:
    """SequenceMatcher ratio in [0..1]; 1.0 = identical."""
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio()


def _cosine_distance(
    a: list[float] | None, b: list[float] | None
) -> float | None:
    """Cosine distance (1 - similarity); None if either vector missing.

    Uses ``is None`` + ``len() == 0`` instead of truthiness because
    pgvector returns numpy arrays for which ``not vector`` raises
    ValueError.
    """
    if a is None or b is None:
        return None
    if len(a) == 0 or len(b) == 0:
        return None
    if len(a) != len(b):
        return None
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return None
    # Coerce to native float — pgvector returns numpy.float32 which
    # is not JSON-serializable when persisted in raw_diff JSONB.
    return float(1.0 - dot / (math.sqrt(na) * math.sqrt(nb)))


def _unified_diff(old: str, new: str) -> list[str]:
    """Truncated unified diff for evidence + LLM prompts."""
    lines = list(
        difflib.unified_diff(
            (old or "").splitlines(),
            (new or "").splitlines(),
            lineterm="",
            n=2,
        )
    )
    return lines[:TEXT_DIFF_MAX_LINES]


def _parsed_diff(old: dict | None, new: dict | None) -> dict:
    """Shallow diff of parsed dicts — what keys changed value or were added/removed."""
    old = old or {}
    new = new or {}
    added = sorted(set(new.keys()) - set(old.keys()))
    removed = sorted(set(old.keys()) - set(new.keys()))
    changed = sorted(
        k for k in set(old.keys()) & set(new.keys()) if old.get(k) != new.get(k)
    )
    return {"added": added, "removed": removed, "changed": changed}
