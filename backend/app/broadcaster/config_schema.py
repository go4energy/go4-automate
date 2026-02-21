"""Broadcaster module interface - config schema, metrics, status."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.module_interface import ModuleInterface
from app.utils.module_registry import register_module


class BroadcasterInterface(ModuleInterface):
    """Broadcaster module standardized interface."""

    MODULE_NAME = "broadcaster"
    PARAMS = [
        {
            "key": "llm_provider",
            "type": "enum",
            "options": ["anthropic", "ollama"],
            "default": "anthropic",
            "description": "LLM-Provider fuer Script-Generierung",
            "affects_kpis": ["episode_quality"],
            "category": "llm",
        },
        {
            "key": "tts_engine",
            "type": "enum",
            "options": ["piper", "disabled"],
            "default": "piper",
            "description": "TTS-Engine fuer Audio-Generierung",
            "affects_kpis": ["episodes_with_audio"],
            "category": "tts",
        },
        {
            "key": "default_voice",
            "type": "string",
            "default": "de_DE-thorsten-high",
            "description": "Standard-Stimme fuer neue Channels",
            "affects_kpis": [],
            "category": "tts",
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
        },
        {
            "key": "self_registration",
            "type": "boolean",
            "default": True,
            "description": "Listener-Selbstregistrierung erlauben",
            "affects_kpis": ["listener_count"],
            "category": "auth",
        },
    ]

    async def get_status(self, db: AsyncSession, tenant_id: str) -> dict:
        """Return broadcaster health and operational status."""
        from app.broadcaster.models import (
            BriefingChannel,
            ListenerUser,
        )
        from app.broadcaster.tts import TTSService
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
            "module": "broadcaster",
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
        """Return broadcaster KPIs."""
        from app.broadcaster.models import (
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
            "module": "broadcaster",
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


broadcaster_interface = BroadcasterInterface()

# Auto-register for settings discovery

register_module(broadcaster_interface)
