"""Briefing module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.services.tenant import TenantService
from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class BriefingInterface(ModuleInterface):
    """Briefing module standardized interface."""

    MODULE_NAME = "briefing"
    PARAMS = [
        {
            "key": "llm_provider",
            "type": "enum",
            "options": ["ollama", "anthropic", "openai"],
            "default": "ollama",
            "description": "LLM-Provider fuer Script-Generierung",
            "affects_kpis": ["episode_quality"],
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
            "description": "Optionaler Modellname fuer den gewaehlten Briefing-LLM-Provider",
            "affects_kpis": ["episode_quality"],
            "category": "llm",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "tts_engine",
            "type": "enum",
            "options": ["piper", "xtts", "disabled"],
            "default": "piper",
            "description": "TTS-Engine fuer Audio-Generierung",
            "affects_kpis": ["episodes_with_audio"],
            "category": "tts",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "medium",
        },
        {
            "key": "default_voice",
            "type": "string",
            "default": "de_DE-thorsten-high",
            "description": "Standard-Stimme fuer neue Channels",
            "affects_kpis": [],
            "category": "tts",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "max_episodes_per_day",
            "type": "integer",
            "min": 1,
            "max": 50,
            "default": 10,
            "description": "Maximale Episoden pro Tag (alle Channels)",
            "affects_kpis": ["episodes_per_day"],
            "category": "limits",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "medium",
        },
        {
            "key": "self_registration",
            "type": "boolean",
            "default": True,
            "description": "Listener-Selbstregistrierung erlauben",
            "affects_kpis": ["listener_count"],
            "category": "auth",
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "secret": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
    ]
    ACTIONS = [
        {
            "key": "run_sources_now",
            "label": "Quellen jetzt abrufen",
            "description": "Fuehrt den Quellenabruf fuer das Briefing sofort aus.",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
        },
        {
            "key": "generate_channel_episode",
            "label": "Channel-Episode erzeugen",
            "description": "Startet die manuelle Generierung einer Briefing-Episode fuer einen Channel.",
            "invokable_by_ai": True,
            "requires_confirmation": True,
            "risk_level": "medium",
            "input_schema": {
                "channel_id": {
                    "type": "integer",
                    "required": True,
                    "description": "ID des Channels",
                }
            },
        },
        {
            "key": "run_personal_briefing",
            "label": "Persoenliches Briefing ausfuehren",
            "description": "Startet einen manuellen Lauf fuer das persoenliche Mail-/Kalender-Briefing.",
            "invokable_by_ai": True,
            "requires_confirmation": False,
            "risk_level": "low",
        },
    ]
    ENDUSER_CONTROLS = [
        {
            "key": "email_enabled",
            "label": "E-Mail-Briefing aktivieren",
            "source": "personal_settings",
            "type": "boolean",
        },
        {
            "key": "calendar_enabled",
            "label": "Kalender-Briefing aktivieren",
            "source": "personal_settings",
            "type": "boolean",
        },
        {
            "key": "delivery_time",
            "label": "Briefing-Uhrzeit",
            "source": "personal_settings",
            "type": "time",
        },
    ]
    CREDENTIALS = [
        {
            "key": "microsoft_client_id",
            "label": "Microsoft Client ID",
            "type": "string",
            "source": "system_config",
            "secret": False,
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "microsoft_client_secret",
            "label": "Microsoft Client Secret",
            "type": "secret",
            "source": "system_config",
            "secret": True,
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "google_client_id",
            "label": "Google Client ID",
            "type": "string",
            "source": "system_config",
            "secret": False,
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
        {
            "key": "google_client_secret",
            "label": "Google Client Secret",
            "type": "secret",
            "source": "system_config",
            "secret": True,
            "editable_by_ai": True,
            "editable_by_enduser": False,
            "requires_confirmation": True,
            "risk_level": "high",
        },
    ]

    async def execute_action(
        self,
        db: AsyncSession,
        tenant_id: str,
        action_key: str,
        payload: dict | None = None,
    ) -> dict:
        """Execute chatbot/admin actions for the briefing module."""
        from app.briefing.service import BriefingService

        payload = payload or {}
        service = BriefingService(db)

        if action_key == "run_sources_now":
            result = await service.run_sources(tenant_id)
            await db.commit()
            return {
                "module": self.MODULE_NAME,
                "action": action_key,
                "status": "ok",
                "result": result,
            }

        if action_key == "generate_channel_episode":
            channel_id = payload.get("channel_id")
            if not isinstance(channel_id, int):
                raise ValidationError("Feld 'channel_id' muss als Integer uebergeben werden")

            tenant = await TenantService(db).get_by_id(tenant_id)
            tenant_config = TenantService.merge_effective_config(
                tenant_id, tenant.config or {}
            )
            episode = await service.generate_episode(tenant_id, channel_id, tenant_config)
            await db.commit()
            return {
                "module": self.MODULE_NAME,
                "action": action_key,
                "status": "ok",
                "result": {
                    "episode_id": episode.id,
                    "channel_id": episode.channel_id,
                    "title": episode.title,
                    "status": episode.status,
                },
            }

        if action_key == "run_personal_briefing":
            user_id = payload.get("user_id")
            if not isinstance(user_id, int):
                raise ValidationError("Feld 'user_id' muss als Integer uebergeben werden")

            result = await service.run_personal_briefing(tenant_id, user_id)
            await db.commit()
            return {
                "module": self.MODULE_NAME,
                "action": action_key,
                "status": "ok",
                "result": result,
            }

        return await super().execute_action(db, tenant_id, action_key, payload)

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return briefing health and operational status."""
        from app.briefing.models import (
            BriefingChannel,
            ListenerUser,
        )
        from app.briefing.tts import TTSService
        from app.config import settings

        channels_result = await db.execute(
            select(
                func.count(BriefingChannel.id).filter(BriefingChannel.active.is_(True)),
                func.count(BriefingChannel.id),
            ).where(BriefingChannel.tenant_id == tenant_id)
        )
        row = channels_result.one()
        active_channels = row[0]

        users_result = await db.execute(
            select(func.count(ListenerUser.id)).where(
                ListenerUser.tenant_id == tenant_id,
                ListenerUser.active.is_(True),
            )
        )
        active_users = users_result.scalar() or 0

        tts = TTSService()

        return {
            "module": "briefing",
            "healthy": True,
            "components": {
                "database": "ok",
                "llm": "ok" if settings.anthropic_api_key else "not_configured",
                "tts": "ok" if tts.is_available() else "disabled",
            },
            "channels_active": active_channels,
            "listener_users": active_users,
        }

    async def get_metrics(
        self, db: AsyncSession, tenant_id: str, days: int = 7
    ) -> dict:
        """Return briefing KPIs."""
        from app.briefing.models import (
            BriefingChannel,
            BriefingEpisode,
            ListenerFeedback,
            ListenerUser,
        )

        cutoff = datetime.utcnow() - timedelta(days=days)

        episodes_count = await db.execute(
            select(func.count(BriefingEpisode.id)).where(
                BriefingEpisode.tenant_id == tenant_id,
                BriefingEpisode.created_at >= cutoff,
            )
        )
        ready_count = await db.execute(
            select(func.count(BriefingEpisode.id)).where(
                BriefingEpisode.tenant_id == tenant_id,
                BriefingEpisode.status == "ready",
                BriefingEpisode.created_at >= cutoff,
            )
        )
        channels_active = await db.execute(
            select(func.count(BriefingChannel.id)).where(
                BriefingChannel.tenant_id == tenant_id,
                BriefingChannel.active.is_(True),
            )
        )
        users_total = await db.execute(
            select(func.count(ListenerUser.id)).where(
                ListenerUser.tenant_id == tenant_id,
            )
        )
        feedback_count = await db.execute(
            select(func.count(ListenerFeedback.id))
            .join(
                BriefingEpisode,
                ListenerFeedback.episode_id == BriefingEpisode.id,
            )
            .where(
                BriefingEpisode.tenant_id == tenant_id,
                ListenerFeedback.created_at >= cutoff,
            )
        )

        episodes_total = episodes_count.scalar() or 0

        return {
            "module": "briefing",
            "period": f"{days}d",
            "metrics": {
                "episodes_total": episodes_total,
                "episodes_ready": ready_count.scalar() or 0,
                "episodes_per_day_avg": round(episodes_total / max(days, 1), 1),
                "channels_active": channels_active.scalar() or 0,
                "listener_users": users_total.scalar() or 0,
                "feedback_count": feedback_count.scalar() or 0,
            },
        }


briefing_interface = BriefingInterface()

# Auto-register for settings discovery

register_module(briefing_interface)
