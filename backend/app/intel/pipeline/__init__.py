"""Intel pipeline stages — fetch, diff, triage, reason, compose."""

from app.intel.pipeline.compose import compose_briefing, default_period_window
from app.intel.pipeline.diff import detect_change
from app.intel.pipeline.fetch import fetch_one
from app.intel.pipeline.reason import reason
from app.intel.pipeline.triage import triage

__all__ = [
    "compose_briefing",
    "default_period_window",
    "detect_change",
    "fetch_one",
    "reason",
    "triage",
]
