"""FastAPI routers."""

from app.routers.ad_campaigns import router as ad_campaigns_router
from app.routers.content import router as content_router
from app.routers.leads import router as leads_router
from app.routers.llm import router as llm_router
from app.routers.prompts import router as prompts_router
from app.routers.templates import router as templates_router
from app.routers.tenants import router as tenants_router

__all__ = [
    "ad_campaigns_router",
    "content_router",
    "leads_router",
    "llm_router",
    "prompts_router",
    "templates_router",
    "tenants_router",
]
