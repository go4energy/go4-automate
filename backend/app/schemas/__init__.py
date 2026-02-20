"""Pydantic schemas — shared schemas only.

Domain module schemas (collector, creator, distributor, crm) are imported
directly from their respective modules (e.g. app.collector.schemas).
"""

from app.schemas.activity import ActivityLogResponse, ActivityStatsResponse
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationListItem,
    ConversationResponse,
)
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.schemas.prompt import (
    PromptCreate,
    PromptExecuteRequest,
    PromptExecuteResponse,
    PromptListItem,
    PromptResponse,
    PromptUpdate,
)
from app.schemas.template import TemplateListItem, TemplateResponse, TemplateUpdate
from app.schemas.tenant import TenantCreate, TenantResponse

__all__ = [
    "ActivityLogResponse",
    "ActivityStatsResponse",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ConversationCreate",
    "ConversationListItem",
    "ConversationResponse",
    "LLMGenerateRequest",
    "LLMGenerateResponse",
    "PromptCreate",
    "PromptExecuteRequest",
    "PromptExecuteResponse",
    "PromptListItem",
    "PromptResponse",
    "PromptUpdate",
    "TemplateListItem",
    "TemplateResponse",
    "TemplateUpdate",
    "TenantCreate",
    "TenantResponse",
]
