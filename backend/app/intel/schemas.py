"""Intel module schemas — Pydantic v2 contracts.

Includes the canonical ``IntelBriefingPayload`` schema with version
guard. ``compose.py`` validates against this schema before writing —
malformed payloads raise instead of being persisted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============== Watch-Target ==============


class WatchTargetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: Literal["competitor", "regulator", "segment"]
    context: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class WatchTargetCreate(WatchTargetBase):
    pass


class WatchTargetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    kind: Literal["competitor", "regulator", "segment"] | None = None
    context: dict[str, Any] | None = None
    is_active: bool | None = None


class WatchTargetResponse(WatchTargetBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Source ==============


class SourceConfig(BaseModel):
    """Adapter-specific config blob — kept loose, validated per-adapter."""

    url: str | None = None
    render_js: bool = False
    user_agent: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    selector: str | None = None  # bs4-CSS selector to focus extraction


class SourceBase(BaseModel):
    adapter: Literal["web", "web_js", "rss", "jobs_board", "structured_api"]
    config: dict[str, Any] = Field(default_factory=dict)
    fetch_interval_sec: int = Field(default=3600, ge=300, le=86400)
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    adapter: (
        Literal["web", "web_js", "rss", "jobs_board", "structured_api"] | None
    ) = None
    config: dict[str, Any] | None = None
    fetch_interval_sec: int | None = Field(None, ge=300, le=86400)
    is_active: bool | None = None


class SourceResponse(SourceBase):
    id: int
    tenant_id: str
    target_id: int
    last_fetched_at: datetime | None
    last_status: str
    consecutive_failures: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============== Adapter Fetch ==============


class FetchResult(BaseModel):
    """What every adapter returns from ``fetch()``.

    Adapters raise ``AdapterError`` on failure — never return ``None``.
    """

    text: str
    parsed: dict[str, Any] = Field(default_factory=dict)
    source_url: str
    fetched_at: datetime
    raw_size_bytes: int | None = None


# ============== Change-Event ==============


class ChangeEventResponse(BaseModel):
    id: int
    tenant_id: str
    source_id: int
    prev_snapshot_id: int | None
    new_snapshot_id: int
    change_type: str
    significance: float
    headline: str | None
    summary: str | None
    impact_assessment: str | None
    evidence: list[dict[str, Any]] | None
    processed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("significance", mode="before")
    @classmethod
    def _coerce_significance(cls, v):
        if v is None:
            return 0.0
        return float(v)


# ============== Triage / Reason LLM contracts ==============


class TriageDecision(BaseModel):
    """Structured output from ``classify_change`` tool (Haiku)."""

    change_type: str = Field(..., min_length=1, max_length=50)
    significance: float = Field(..., ge=0.0, le=1.0)


class ReasonOutput(BaseModel):
    """JSON-mode output from the reasoning step (Sonnet)."""

    headline: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1)
    impact_assessment: str = Field(..., min_length=1)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


# ============== Briefing Payload (canonical) ==============


class _Period(BaseModel):
    start: datetime
    end: datetime


class _Evidence(BaseModel):
    url: str
    fetched_at: datetime


class _Section(BaseModel):
    type: Literal[
        "competitor_change",
        "market_gap_hypothesis",
        "regulatory_alert",
    ]
    significance: float = Field(..., ge=0.0, le=1.0)
    headline: str
    watch_target: str
    change_type: str
    summary: str
    impact_for_us: str
    suggested_action: str | None = None
    evidence: list[_Evidence] = Field(default_factory=list)
    engagement_event_id: int | None = None


class _Stats(BaseModel):
    sources_checked: int = 0
    changes_detected: int = 0
    after_triage: int = 0


class IntelBriefingPayload(BaseModel):
    """Canonical persisted payload for ``intel_briefing.payload``.

    ``compose.py`` MUST validate against this model. Malformed payloads
    raise ``ValidationError`` — never get written.
    """

    schema_version: Literal["1.0"] = Field("1.0", alias="_schema_version")
    briefing_type: Literal["intel_daily", "intel_weekly"] = "intel_daily"
    tenant_id: str
    period: _Period
    tts_summary: str = Field(..., max_length=600)
    tts_summary_duration_estimate_sec: int = 0
    sections: list[_Section] = Field(default_factory=list)
    stats: _Stats = Field(default_factory=_Stats)

    model_config = ConfigDict(populate_by_name=True)


class BriefingResponse(BaseModel):
    id: int
    tenant_id: str
    briefing_uuid: str
    period_start: datetime
    period_end: datetime
    payload: dict[str, Any]
    tts_summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
