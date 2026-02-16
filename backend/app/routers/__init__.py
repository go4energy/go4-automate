"""FastAPI routers."""

from app.routers.leads import router as leads_router
from app.routers.llm import router as llm_router
from app.routers.templates import router as templates_router
from app.routers.tenants import router as tenants_router

__all__ = [
    "leads_router",
    "llm_router",
    "templates_router",
    "tenants_router",
]
