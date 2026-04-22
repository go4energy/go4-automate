"""Leadgen module interface - config schema, credentials, status, actions."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class LeadgenInterface(ModuleInterface):
    """Leadgen module standardised interface."""

    MODULE_NAME = "leadgen"

    PARAMS = [
        {
            "key": "places_qps",
            "type": "integer",
            "min": 1,
            "max": 30,
            "default": 10,
            "description": "Max. Google-Places-Requests pro Sekunde (konservativ halten).",
            "affects_kpis": ["places_discovered"],
            "category": "places",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "max_places_pages_per_query",
            "type": "integer",
            "min": 1,
            "max": 3,
            "default": 3,
            "description": "Maximale Seiten pro Query (3 = max. 60 Ergebnisse).",
            "affects_kpis": ["places_discovered"],
            "category": "places",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "impressum_per_host_delay_s",
            "type": "integer",
            "min": 1,
            "max": 60,
            "default": 5,
            "description": "Sekunden Abstand zwischen Requests zum gleichen Host.",
            "affects_kpis": ["impressum_success_rate"],
            "category": "impressum",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "respect_robots_txt",
            "type": "boolean",
            "default": True,
            "description": "robots.txt beim Impressum-Crawling beachten.",
            "affects_kpis": [],
            "category": "impressum",
            "editable_by_ai": False,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "crawler_user_agent",
            "type": "string",
            "default": "go4energy-leadbot/1.0 (kontakt@go4.energy)",
            "description": "User-Agent fuer Impressum-Crawler - muss Kontakt offenlegen.",
            "affects_kpis": [],
            "category": "impressum",
            "editable_by_ai": False,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "llm_model",
            "type": "string",
            "default": "claude-haiku-4-5",
            "description": "Claude-Modell fuer Stage 3 (Business-Intelligence).",
            "affects_kpis": ["llm_cost", "enrichment_quality"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "llm_max_pages_per_company",
            "type": "integer",
            "min": 1,
            "max": 10,
            "default": 4,
            "description": "Max. Unterseiten pro Firma fuer LLM-Analyse.",
            "affects_kpis": ["llm_cost"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "llm_max_input_tokens_per_company",
            "type": "integer",
            "min": 1000,
            "max": 50000,
            "default": 10000,
            "description": "Token-Budget pro Firma im LLM-Call.",
            "affects_kpis": ["llm_cost"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "excluded_website_hosts",
            "type": "string",
            "default": (
                "facebook.com,instagram.com,business.site,"
                "gelbeseiten.de,11880.com,yelp.com,yelp.de"
            ),
            "description": "Hosts, die beim Impressum-Scraping ignoriert werden (Komma-getrennt).",
            "affects_kpis": [],
            "category": "impressum",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
    ]

    ACTIONS = [
        {
            "key": "start_run",
            "label": "Run starten",
            "description": "Startet einen neuen Pipeline-Run fuer eine Kampagne.",
            "invokable_by_ai": True,
            "requires_confirmation": True,
            "risk_level": "medium",
            "input_schema": {"campaign_id": "integer"},
        },
        {
            "key": "pause_run",
            "label": "Run pausieren",
            "description": "Pausiert einen laufenden Run.",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
            "input_schema": {"run_id": "integer"},
        },
        {
            "key": "resume_run",
            "label": "Run fortsetzen",
            "description": "Setzt einen pausierten Run fort.",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
            "input_schema": {"run_id": "integer"},
        },
    ]

    CREDENTIALS = [
        {
            "key": "google_places_api_key",
            "label": "Google Places API Key",
            "description": "API Key fuer Google Places (New). Wird beim Discovery-Stage genutzt.",
            "secret": True,
            "source": "system_config",
            "required_for": ["start_run"],
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return module health status."""
        from app.leadgen.models import LeadgenCampaign, LeadgenRun

        campaigns = await db.execute(
            select(func.count(LeadgenCampaign.id)).where(
                LeadgenCampaign.tenant_id == tenant_id,
            )
        )
        running_runs = await db.execute(
            select(func.count(LeadgenRun.id)).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.status == "running",
            )
        )
        return {
            "module": "leadgen",
            "healthy": True,
            "components": {
                "database": "ok",
                "campaigns": campaigns.scalar() or 0,
                "running_runs": running_runs.scalar() or 0,
            },
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return KPIs."""
        from datetime import datetime, timedelta

        from app.leadgen.models import LeadgenPlace, LeadgenRun

        since = datetime.utcnow() - timedelta(days=days)

        places = await db.execute(
            select(func.count(LeadgenPlace.id)).where(
                LeadgenPlace.tenant_id == tenant_id,
                LeadgenPlace.created_at >= since,
            )
        )
        cost = await db.execute(
            select(func.coalesce(func.sum(LeadgenRun.cost_cents), 0)).where(
                LeadgenRun.tenant_id == tenant_id,
                LeadgenRun.created_at >= since,
            )
        )

        return {
            "module": "leadgen",
            "period": f"{days}d",
            "metrics": {
                "places_discovered": places.scalar() or 0,
                "total_cost_cents": cost.scalar() or 0,
            },
        }


interface = LeadgenInterface()
register_module(interface)
