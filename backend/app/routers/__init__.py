"""FastAPI routers - shared routers only.

Domain module routers are auto-discovered from __manifest__.py files
and registered via module_discovery.register_routers() in main.py.
"""

from app.routers.activity import router as activity_router
from app.routers.chat import router as chat_router
from app.routers.llm import router as llm_router
from app.routers.modules import router as modules_router
from app.routers.prompts import router as prompts_router
from app.routers.streams import router as streams_router
from app.routers.tags import router as tags_router
from app.routers.templates import router as templates_router
from app.routers.tenants import router as tenants_router

__all__ = [
    "activity_router",
    "chat_router",
    "llm_router",
    "modules_router",
    "prompts_router",
    "streams_router",
    "tags_router",
    "templates_router",
    "tenants_router",
]
