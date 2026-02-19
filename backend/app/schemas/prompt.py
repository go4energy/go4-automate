"""Prompt registry schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptVariableDefinition(BaseModel):
    """Definition of a template variable."""

    name: str
    type: str = "string"
    required: bool = True
    default: str | None = None
    description: str | None = None


class PromptCreate(BaseModel):
    """Schema for creating a prompt."""

    slug: str = Field(..., pattern=r"^[a-z0-9\-]+$", max_length=100)
    name: str = Field(..., max_length=200)
    description: str | None = None
    category: str = "general"
    system_prompt: str
    user_prompt: str
    variables: list[PromptVariableDefinition] | None = None
    output_format: str = "text"
    output_schema: dict | None = None
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=16384)


class PromptUpdate(BaseModel):
    """Schema for updating a prompt (all fields optional)."""

    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    category: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    variables: list[PromptVariableDefinition] | None = None
    output_format: str | None = None
    output_schema: dict | None = None
    provider: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=16384)
    is_active: bool | None = None


class PromptResponse(BaseModel):
    """Full prompt response."""

    id: int
    tenant_id: str
    slug: str
    name: str
    description: str | None = None
    category: str
    system_prompt: str
    user_prompt: str
    variables: list[PromptVariableDefinition] | None = None
    output_format: str
    output_schema: dict | None = None
    provider: str
    model: str
    temperature: float
    max_tokens: int
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptListItem(BaseModel):
    """Lightweight prompt for list views (no prompt texts)."""

    id: int
    tenant_id: str
    slug: str
    name: str
    description: str | None = None
    category: str
    output_format: str
    provider: str
    model: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptExecuteRequest(BaseModel):
    """Schema for executing a prompt by slug."""

    prompt_slug: str
    variables: dict = Field(default_factory=dict)


class PromptExecuteResponse(BaseModel):
    """Schema for prompt execution result."""

    prompt_slug: str
    provider: str
    model: str
    output_format: str
    result: str | dict
    version: int
