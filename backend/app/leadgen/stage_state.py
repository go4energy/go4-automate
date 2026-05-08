"""Per-stage progress tracking for leadgen runs.

The frontend renders each run as a timeline (Places → Impressum → Verify → LLM).
Each stage carries its own status, timestamps, counters and cost so the user
can see at a glance what happened in which order — including the new Verify
sub-step (Serper) which today hides inside the LLM stage.

The stage block lives at ``run.stage_state["stages"][<stage_key>]`` and is
written by the worker as it progresses. Schema is intentionally permissive:

    {
        "status": "pending|running|completed|skipped|failed",
        "started_at":   "<isoformat>",
        "completed_at": "<isoformat>",
        "total":      int,
        "processed":  int,
        "succeeded":  int,
        "failed":     int,
        "cost_cents": int,
        "reason":     str,                # only when status=skipped
        "extra":      {...stage-specific keys...}
    }

Helper functions are pure dict mutators — they take and return the full
``state`` dict so the worker can call them inline before re-assigning
``run.stage_state``. SQLAlchemy's JSONB tracking only fires on full reassign,
which the existing worker already does (`run.stage_state = dict(state)`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Canonical stage keys / order. The frontend renders rows in this order.
STAGE_KEYS: tuple[str, ...] = (
    "places",
    "impressum",
    "verify",
    "llm",
    "linkedin",
    "apollo",
)


def _stages_block(state: dict[str, Any]) -> dict[str, Any]:
    """Return (and lazily create) the ``stages`` sub-dict on ``state``."""
    block = state.get("stages")
    if not isinstance(block, dict):
        block = {}
        state["stages"] = block
    return block


def _stage_entry(state: dict[str, Any], key: str) -> dict[str, Any]:
    block = _stages_block(state)
    entry = block.get(key)
    if not isinstance(entry, dict):
        entry = {}
        block[key] = entry
    return entry


def mark_stage_running(state: dict[str, Any], key: str) -> None:
    """Idempotent: only sets ``started_at`` once. Status moves to running."""
    entry = _stage_entry(state, key)
    if "started_at" not in entry:
        entry["started_at"] = datetime.utcnow().isoformat()
    entry["status"] = "running"


def mark_stage_completed(state: dict[str, Any], key: str) -> None:
    entry = _stage_entry(state, key)
    if "started_at" not in entry:
        # Stage closed without ever being marked running — synthesise both
        # timestamps so duration math doesn't blow up downstream.
        entry["started_at"] = datetime.utcnow().isoformat()
    entry["completed_at"] = datetime.utcnow().isoformat()
    entry["status"] = "completed"


def mark_stage_skipped(state: dict[str, Any], key: str, *, reason: str) -> None:
    entry = _stage_entry(state, key)
    entry["status"] = "skipped"
    entry["reason"] = reason


def mark_stage_failed(state: dict[str, Any], key: str, *, error: str) -> None:
    entry = _stage_entry(state, key)
    entry["status"] = "failed"
    entry["error"] = error[:500]
    entry["completed_at"] = datetime.utcnow().isoformat()


def update_stage_counters(
    state: dict[str, Any],
    key: str,
    *,
    delta: dict[str, int] | None = None,
    set_values: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Merge counters into the stage entry.

    ``delta``     — keys that get incremented (existing value + delta value)
    ``set_values`` — keys that get overwritten
    ``extra``     — merged into ``entry["extra"]`` (also dict-merge style)
    """
    entry = _stage_entry(state, key)
    if delta:
        for k, v in delta.items():
            entry[k] = int(entry.get(k, 0) or 0) + int(v)
    if set_values:
        for k, v in set_values.items():
            entry[k] = v
    if extra:
        ext = entry.get("extra")
        if not isinstance(ext, dict):
            ext = {}
            entry["extra"] = ext
        ext.update(extra)


__all__ = [
    "STAGE_KEYS",
    "mark_stage_completed",
    "mark_stage_failed",
    "mark_stage_running",
    "mark_stage_skipped",
    "update_stage_counters",
]
