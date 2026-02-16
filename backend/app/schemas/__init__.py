"""Pydantic schemas."""

from app.schemas.lead import (
    LeadCreate,
    LeadFollowupPause,
    LeadResponse,
    LeadStatusUpdate,
)
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.schemas.template import TemplateListItem, TemplateResponse, TemplateUpdate
from app.schemas.tenant import TenantCreate, TenantResponse

__all__ = [
    "LLMGenerateRequest",
    "LLMGenerateResponse",
    "LeadCreate",
    "LeadFollowupPause",
    "LeadResponse",
    "LeadStatusUpdate",
    "TemplateListItem",
    "TemplateResponse",
    "TemplateUpdate",
    "TenantCreate",
    "TenantResponse",
]
