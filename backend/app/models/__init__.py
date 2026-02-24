"""SQLAlchemy models — auto-discovered from domain modules + explicit shared models."""

from pathlib import Path

from app.utils.module_discovery import discover_manifests, register_models

# Auto-discover and import domain module models (collector, creator, distributor, crm, briefing, etc.)
_manifests = discover_manifests(Path(__file__).resolve().parent.parent)
register_models(_manifests)

# Shared models (no __manifest__.py, live in app/models/)
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.chat_message import ChatMessage  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.prompt import Prompt  # noqa: E402
from app.models.stream import Stream  # noqa: E402
from app.models.tag import Tag  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402

__all__ = [
    "ActivityLog",
    "ChatMessage",
    "Conversation",
    "Prompt",
    "Stream",
    "Tag",
    "Tenant",
]
