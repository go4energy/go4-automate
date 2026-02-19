"""Pydantic schemas."""

from app.schemas.activity import ActivityLogResponse, ActivityStatsResponse
from app.schemas.ad_campaign import (
    AdCampaignCreate,
    AdCampaignResponse,
    AdCampaignUpdate,
)
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ConversationCreate,
    ConversationListItem,
    ConversationResponse,
)
from app.schemas.content import (
    ContentCalendarCreate,
    ContentCalendarResponse,
    ContentPieceCreate,
    ContentPieceResponse,
    ContentPieceUpdate,
)
from app.schemas.lead import (
    LeadCreate,
    LeadFollowupPause,
    LeadResponse,
    LeadStatusUpdate,
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
from app.schemas.research import (
    ResearchFindingListItem,
    ResearchFindingResponse,
    ResearchFindingStatusUpdate,
    ResearchRunRequest,
    ResearchRunResponse,
    ResearchSourceCreate,
    ResearchSourceResponse,
    ResearchSourceUpdate,
    TopicGenerateRequest,
    TopicSuggestionCreate,
    TopicSuggestionListItem,
    TopicSuggestionResponse,
    TopicSuggestionUpdate,
)
from app.schemas.template import TemplateListItem, TemplateResponse, TemplateUpdate
from app.schemas.tenant import TenantCreate, TenantResponse

__all__ = [
    "ActivityLogResponse",
    "ActivityStatsResponse",
    "AdCampaignCreate",
    "AdCampaignResponse",
    "AdCampaignUpdate",
    "ChatMessageCreate",
    "ChatMessageResponse",
    "ContentCalendarCreate",
    "ContentCalendarResponse",
    "ContentPieceCreate",
    "ContentPieceResponse",
    "ContentPieceUpdate",
    "ConversationCreate",
    "ConversationListItem",
    "ConversationResponse",
    "LLMGenerateRequest",
    "LLMGenerateResponse",
    "LeadCreate",
    "LeadFollowupPause",
    "LeadResponse",
    "LeadStatusUpdate",
    "PromptCreate",
    "PromptExecuteRequest",
    "PromptExecuteResponse",
    "PromptListItem",
    "PromptResponse",
    "PromptUpdate",
    "ResearchFindingListItem",
    "ResearchFindingResponse",
    "ResearchFindingStatusUpdate",
    "ResearchRunRequest",
    "ResearchRunResponse",
    "ResearchSourceCreate",
    "ResearchSourceResponse",
    "ResearchSourceUpdate",
    "TemplateListItem",
    "TemplateResponse",
    "TemplateUpdate",
    "TenantCreate",
    "TenantResponse",
    "TopicGenerateRequest",
    "TopicSuggestionCreate",
    "TopicSuggestionListItem",
    "TopicSuggestionResponse",
    "TopicSuggestionUpdate",
]
