"""Typed parsers for per-source campaign config.

leadgen_campaigns.source_config is a JSONB blob whose shape depends on
``source``. Parsing through these Pydantic models keeps router, service and
worker code on a single source of truth for defaults and validation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GoogleGeographicScope(BaseModel):
    """Geographic scope for a google_places source.

    Exactly one of (mode == 'germany' | 'austria' | 'switzerland' |
    'bundesland' | 'circle') with the matching fields populated.
    """

    mode: Literal["germany", "austria", "switzerland", "bundesland", "circle"] = (
        "germany"
    )
    bundesland: str | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    radius_km: float | None = Field(default=None, ge=1, le=500)

    @field_validator("bundesland", mode="after")
    @classmethod
    def _bundesland_lower(cls, v: str | None) -> str | None:
        return v.lower().replace("-", "_").replace(" ", "_") if v else None


class GoogleSearchModes(BaseModel):
    """Which Places API endpoints the worker should hit per tile."""

    nearby: bool = True
    text: bool = True


class LLMStageConfig(BaseModel):
    """Stage 3 (LLM homepage analysis) parameters.

    target_profile and prompt_template are meant to be user-editable; the rest
    are operational knobs with sensible defaults.
    """

    # Optional pre-LLM verification: run a Serper web search for places that
    # Google Places returned with no website, to filter out the false-positive
    # "no homepage" cases (places that DO have a homepage which simply isn't
    # linked in Google's data). Defaults on for new campaigns; degrades to
    # no-op when SERPER_API_KEY is not set.
    verify_no_website_via_serper: bool = True
    serper_blacklist_extra: list[str] = Field(
        default_factory=list,
        description=(
            "Additional hosts to ignore in the Serper-verify heuristic on top "
            "of the built-in directory/portal blacklist."
        ),
        max_length=50,
    )

    # User-editable analysis config
    target_profile: str = Field(
        default="",
        max_length=4000,
        description=(
            "Free-text description of the ideal lead. Used as context for the "
            "LLM when scoring each place."
        ),
    )
    output_description: str = Field(
        default="",
        max_length=4000,
        description=(
            "Free-text description of what the LLM should produce as analysis "
            "output (beyond the default fields). E.g. 'kurze Zusammenfassung "
            "der Tätigkeiten, Hinweise auf Wallbox-Kapazität, Mitarbeiterzahl "
            "wenn erkennbar'."
        ),
    )
    prompt_template: str = Field(
        default="",
        max_length=8000,
        description=(
            "LLM prompt template. Must contain the placeholders "
            "{target_profile} and {content}. Leave empty to use the built-in "
            "default."
        ),
    )

    # LLM operational
    provider: str = "anthropic"
    model: str = Field(default="claude-haiku-4-5", max_length=100)

    # Fetch + batch operational
    max_concurrency: int = Field(default=5, ge=1, le=50)
    http_timeout_s: float = Field(default=15.0, ge=1.0, le=120.0)
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; go4energy-leadgen/1.0)",
        max_length=200,
    )
    max_places_per_run: int = Field(default=2000, ge=1, le=100_000)
    max_html_chars: int = Field(default=15_000, ge=1_000, le=100_000)
    paths_to_fetch: list[str] = Field(
        default_factory=lambda: [
            "/",
            "/impressum",
            "/impressum/",
            "/ueber-uns",
            "/ueber-uns/",
            "/about",
            "/leistungen",
            "/services",
            "/kontakt",
        ],
        max_length=20,
    )


class ImpressumStageConfig(BaseModel):
    """Stage 2 (Impressum scraping) parameters.

    Governs the HTTP fetcher and batch behaviour; parsing rules live in code.
    """

    max_concurrency: int = Field(default=5, ge=1, le=50)
    http_timeout_s: float = Field(default=15.0, ge=1.0, le=120.0)
    user_agent: str = Field(
        default="Mozilla/5.0 (compatible; go4energy-leadgen/1.0)",
        max_length=200,
    )
    respect_robots_txt: bool = False
    max_places_per_run: int = Field(default=2000, ge=1, le=100_000)
    paths_to_try: list[str] = Field(
        default_factory=lambda: [
            "/impressum",
            "/impressum/",
            "/impressum.html",
            "/de/impressum",
            "/kontakt",
            "/kontakt/",
            "/legal/impressum",
        ],
        max_length=20,
    )


class GooglePlacesSourceConfig(BaseModel):
    """Full source_config payload for ``source='google_places'``."""

    search_modes: GoogleSearchModes = Field(default_factory=GoogleSearchModes)
    nearby_types: list[str] = Field(default_factory=list)
    text_synonyms: list[str] = Field(default_factory=list)
    geographic: GoogleGeographicScope = Field(default_factory=GoogleGeographicScope)
    min_tile_km: float = Field(default=10.0, ge=1.0, le=200.0)
    max_api_calls: int = Field(default=2000, ge=1, le=100_000)
    language_code: str = "de"
    region_code: str = "DE"
    # Pipeline auto-chain mode:
    # - smart : places -> llm (LLM extracts impressum + analysis in one pass) [default]
    # - cheap : places -> impressum (regex only, no LLM cost)
    # - legacy: places -> impressum -> llm (regex first, then LLM enrichment)
    pipeline_mode: Literal["smart", "cheap", "legacy"] = "smart"
    # Sales-signal: flag places without an online appointment offer reachable
    # through Google. Off by default — only relevant for verticals where
    # online booking is a real differentiator (doctors, salons, tax offices).
    flag_no_calendar: bool = False
    impressum: ImpressumStageConfig = Field(default_factory=ImpressumStageConfig)
    llm: LLMStageConfig = Field(default_factory=LLMStageConfig)


def parse_source_config(source: str, raw: dict) -> GooglePlacesSourceConfig:
    """Parse source_config into the correct model based on source."""
    if source == "google_places":
        return GooglePlacesSourceConfig.model_validate(raw or {})
    raise ValueError(f"unknown source: {source!r}")
