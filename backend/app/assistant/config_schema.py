"""Assistant module interface - config schema, metrics, status."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class AssistantInterface(ModuleInterface):
    """Assistant module standardised interface."""

    MODULE_NAME = "assistant"

    PARAMS = [
        {
            "key": "llm_provider",
            "type": "enum",
            "options": ["ollama", "anthropic", "openai"],
            "default": "ollama",
            "description": "LLM-Provider fuer Klassifikation und Briefing",
            "affects_kpis": ["briefing_quality"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "llm_model",
            "type": "string",
            "default": "",
            "description": "Modellname fuer den gewaehlten LLM-Provider",
            "affects_kpis": ["briefing_quality"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "tts_provider",
            "type": "enum",
            "options": ["piper", "xtts", "disabled"],
            "default": "piper",
            "description": "TTS-Engine fuer Audio-Briefing",
            "affects_kpis": ["audio_briefings"],
            "category": "tts",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "tts_voice",
            "type": "string",
            "default": "de_DE-thorsten-high",
            "description": "Standard-Stimme fuer Audio-Briefings",
            "affects_kpis": [],
            "category": "tts",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "stt_provider",
            "type": "enum",
            "options": ["faster-whisper", "openai", "disabled"],
            "default": "faster-whisper",
            "description": "STT-Provider fuer Spracheingabe",
            "affects_kpis": [],
            "category": "stt",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "autopilot_enabled",
            "type": "boolean",
            "default": False,
            "description": "Automatische Low-/Medium-Risk-Aktionen aktivieren",
            "affects_kpis": ["auto_actions"],
            "category": "automation",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "autopilot_min_confidence",
            "type": "number",
            "min": 0,
            "max": 1,
            "default": 0.85,
            "description": "Mindest-Confidence fuer autopilot-faehige Vorschlaege",
            "affects_kpis": ["auto_actions"],
            "category": "automation",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "autopilot_max_rule_risk",
            "type": "enum",
            "options": ["low", "medium", "high"],
            "default": "medium",
            "description": "Hoechste Risikostufe fuer autopilot-faehige Regeln",
            "affects_kpis": ["auto_actions"],
            "category": "automation",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "suggestion_min_confidence",
            "type": "number",
            "min": 0,
            "max": 1,
            "default": 0.7,
            "description": "Untergrenze fuer sichtbare Regelvorschlaege",
            "affects_kpis": ["briefing_quality"],
            "category": "automation",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "max_items_per_run",
            "type": "integer",
            "min": 1,
            "max": 200,
            "default": 30,
            "description": "Maximale Items pro Briefing-Lauf",
            "affects_kpis": ["briefing_coverage"],
            "category": "briefing",
            "editable_by_ai": True,
            "editable_by_enduser": True,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
    ]

    ACTIONS = [
        {
            "key": "run_briefing",
            "label": "Briefing jetzt erzeugen",
            "description": "Startet einen Briefing-Lauf fuer den aktuellen User",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
            "input_schema": {},
        },
        {
            "key": "sync_sources",
            "label": "Quellen synchronisieren",
            "description": "Holt neue Mails/Termine von allen aktiven Quellen",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
            "input_schema": {},
        },
    ]

    CREDENTIALS = []

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return module health status."""
        from app.assistant.models import AssistantProfile, AssistantSource

        profiles = await db.execute(
            select(func.count(AssistantProfile.id)).where(
                AssistantProfile.tenant_id == tenant_id,
                AssistantProfile.active.is_(True),
            )
        )
        sources = await db.execute(
            select(func.count(AssistantSource.id)).where(
                AssistantSource.tenant_id == tenant_id,
            )
        )
        return {
            "module": "assistant",
            "healthy": True,
            "components": {
                "database": "ok",
                "active_profiles": profiles.scalar() or 0,
                "connected_sources": sources.scalar() or 0,
            },
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return KPIs."""
        from datetime import datetime, timedelta

        from app.assistant.models import AssistantAction, AssistantItem

        since = datetime.utcnow() - timedelta(days=days)

        items_count = await db.execute(
            select(func.count(AssistantItem.id)).where(
                AssistantItem.tenant_id == tenant_id,
                AssistantItem.created_at >= since,
            )
        )
        actions_count = await db.execute(
            select(func.count(AssistantAction.id)).where(
                AssistantAction.tenant_id == tenant_id,
                AssistantAction.created_at >= since,
            )
        )

        return {
            "module": "assistant",
            "period": f"{days}d",
            "metrics": {
                "items_ingested": items_count.scalar() or 0,
                "actions_total": actions_count.scalar() or 0,
            },
        }

    async def execute_action(
        self,
        db: AsyncSession,
        tenant_id: str,
        action_key: str,
        payload: dict | None = None,
    ) -> dict:
        """Execute admin/AI action."""
        if action_key == "run_briefing":
            from app.assistant.service import AssistantService

            user_id = (payload or {}).get("user_id")
            if not user_id:
                return {
                    "module": self.MODULE_NAME,
                    "action": action_key,
                    "status": "error",
                    "result": {"message": "user_id erforderlich"},
                }
            svc = AssistantService(db)
            result = await svc.run_briefing(tenant_id, user_id)
            await db.commit()
            return {
                "module": self.MODULE_NAME,
                "action": action_key,
                "status": "ok",
                "result": result,
            }
        if action_key == "sync_sources":
            from app.assistant.intake import AssistantIntakeService

            user_id = (payload or {}).get("user_id")
            if not user_id:
                return {
                    "module": self.MODULE_NAME,
                    "action": action_key,
                    "status": "error",
                    "result": {"message": "user_id erforderlich"},
                }
            intake = AssistantIntakeService(db)
            result = await intake.run_intake(tenant_id, user_id)
            await db.commit()
            return {
                "module": self.MODULE_NAME,
                "action": action_key,
                "status": "ok",
                "result": result,
            }
        return await super().execute_action(db, tenant_id, action_key, payload)


interface = AssistantInterface()
register_module(interface)
