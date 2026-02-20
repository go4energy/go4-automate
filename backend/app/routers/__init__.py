"""FastAPI routers - shared routers only.

Domain module routers (collector, creator, distributor, crm) are registered
directly from their respective modules in main.py.
"""

from app.routers.activity import router as activity_router
from app.routers.chat import router as chat_router
from app.routers.llm import router as llm_router
from app.routers.prompts import router as prompts_router
from app.routers.templates import router as templates_router
from app.routers.tenants import router as tenants_router

__all__ = [
    "activity_router",
    "chat_router",
    "llm_router",
    "prompts_router",
    "templates_router",
    "tenants_router",
]
