"""Funnels module - prospecting and lead generation before CRM."""

from app.funnels.models import (
    Funnel,
    FunnelActivity,
    FunnelCompany,
    FunnelHandoff,
    FunnelProspect,
    FunnelStage,
)
from app.funnels.n8n_router import n8n_router
from app.funnels.router import router

__all__ = [
    "Funnel",
    "FunnelActivity",
    "FunnelCompany",
    "FunnelHandoff",
    "FunnelProspect",
    "FunnelStage",
    "n8n_router",
    "router",
]
