"""Pydantic schemas for AI Setup module."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ═══════════════════════════════════════════════════════════════════════════════
# Module Context Schemas
# ═══════════════════════════════════════════════════════════════════════════════


class ModuleContextBase(BaseModel):
    """Base schema for module context."""

    context_data: dict[str, Any] = Field(default_factory=dict)


class ModuleContextCreate(ModuleContextBase):
    """Schema for creating a module context."""

    module: str


class ModuleContextUpdate(BaseModel):
    """Schema for updating module context."""

    context_data: dict[str, Any] | None = None
    onboarding_completed: bool | None = None
    onboarding_notes: str | None = None


class ModuleContextResponse(ModuleContextBase):
    """Response schema for module context."""

    id: int
    tenant_id: str
    module: str
    onboarding_completed: bool
    onboarding_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContextVariableUpdate(BaseModel):
    """Schema for updating a single context variable."""

    key: str
    value: Any


class ContextVariableDelete(BaseModel):
    """Schema for deleting a context variable."""

    key: str


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Schemas (extended for AI setup)
# ═══════════════════════════════════════════════════════════════════════════════


class PromptBase(BaseModel):
    """Base schema for prompts."""

    slug: str
    name: str
    description: str | None = None
    category: str = "general"
    module: str = "global"
    prompt_type: str = "productive"  # "setup" or "productive"
    system_prompt: str
    user_prompt: str
    variables: dict | None = None
    variables_schema: dict | None = None
    output_format: str = "text"
    output_schema: dict | None = None
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048


class PromptCreate(PromptBase):
    """Schema for creating a prompt."""

    pass


class PromptUpdate(BaseModel):
    """Schema for updating a prompt."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    prompt_type: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: dict | None = None
    variables_schema: dict | None = None
    output_format: str | None = None
    output_schema: dict | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    is_active: bool | None = None


class PromptResponse(PromptBase):
    """Response schema for prompts."""

    id: int
    tenant_id: str
    is_system: bool
    is_active: bool
    version: int
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptListResponse(BaseModel):
    """Response schema for listing prompts."""

    setup: list[PromptResponse] = []
    productive: list[PromptResponse] = []


# ═══════════════════════════════════════════════════════════════════════════════
# Onboarding Chat Schemas
# ═══════════════════════════════════════════════════════════════════════════════


class OnboardingChatMessage(BaseModel):
    """Schema for a single chat message in onboarding."""

    role: str  # "user" or "assistant"
    content: str


class OnboardingChatRequest(BaseModel):
    """Request schema for onboarding chat."""

    message: str
    prompt_key: str = "onboarding"


class OnboardingChatResponse(BaseModel):
    """Response schema for onboarding chat."""

    message: str
    is_complete: bool = False
    extracted_data: dict[str, Any] | None = None
    prompts_generated: list[str] = []  # List of generated prompt slugs


class OnboardingStartResponse(BaseModel):
    """Response when starting an onboarding session."""

    conversation_id: int
    first_message: str


class OnboardingResetResponse(BaseModel):
    """Response when resetting onboarding."""

    success: bool
    message: str


# ═══════════════════════════════════════════════════════════════════════════════
# Module Parameter Schemas
# ═══════════════════════════════════════════════════════════════════════════════


class ModuleParameterBase(BaseModel):
    """Base schema for module parameters."""

    variable: str
    description: str
    value: str | None = None
    var_type: str = "string"  # string, array, boolean, number
    required: bool = True
    sort_order: int = 0


class ModuleParameterCreate(ModuleParameterBase):
    """Schema for creating a module parameter."""

    pass


class ModuleParameterUpdate(BaseModel):
    """Schema for updating a module parameter."""

    description: str | None = None
    value: str | None = None
    var_type: str | None = None
    required: bool | None = None
    sort_order: int | None = None


class ModuleParameterResponse(ModuleParameterBase):
    """Response schema for module parameters."""

    id: int
    tenant_id: str
    module: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModuleParameterBulkCreate(BaseModel):
    """Schema for bulk creating parameters."""

    parameters: list[ModuleParameterCreate]


class ModuleParameterValueUpdate(BaseModel):
    """Schema for updating just the value of a parameter."""

    value: str | None
