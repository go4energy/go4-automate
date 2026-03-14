"""SQLAlchemy models — auto-discovered from domain modules + explicit shared models."""

import importlib
from pathlib import Path


def _import_domain_model_modules() -> None:
    """Import all domain ``models.py`` modules directly.

    Using the filesystem is more robust here than manifest-driven discovery because
    model registration should not depend on unrelated manifest/config import side
    effects.
    """

    app_dir = Path(__file__).resolve().parent.parent
    skip_dirs = {"__pycache__", "utils", "routers", "models", "services"}

    for models_path in app_dir.glob("*/models.py"):
        module_name = models_path.parent.name
        if module_name.startswith("_") or module_name in skip_dirs:
            continue
        importlib.import_module(f"app.{module_name}.models")


_import_domain_model_modules()

# Shared models (no __manifest__.py, live in app/models/)
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.chat_message import ChatMessage  # noqa: E402
from app.models.conversation import Conversation  # noqa: E402
from app.models.module_context import ModuleContext  # noqa: E402
from app.models.module_parameter import ModuleParameter  # noqa: E402
from app.models.prompt import Prompt  # noqa: E402
from app.models.stream import Stream  # noqa: E402
from app.models.tag import Tag  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402

__all__ = [
    "ActivityLog",
    "ChatMessage",
    "Conversation",
    "ModuleContext",
    "ModuleParameter",
    "Prompt",
    "Stream",
    "Tag",
    "Tenant",
]
