"""Funnels module - prospecting and lead generation before CRM."""

from app.funnels.models import (
    Funnel,
    FunnelActivity,
    FunnelCompany,
    FunnelHandoff,
    FunnelProspect,
    FunnelStage,
)
from app.funnels.router import router
from app.funnels.n8n_router import n8n_router

__all__ = [
    "Funnel",
    "FunnelStage",
    "FunnelCompany",
    "FunnelProspect",
    "FunnelActivity",
    "FunnelHandoff",
    "router",
    "n8n_router",
]
