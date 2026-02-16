"""LLM schemas."""

from pydantic import BaseModel


class LLMGenerateRequest(BaseModel):
    """Schema for LLM generation request."""

    task: str
    prompt: str


class LLMGenerateResponse(BaseModel):
    """Schema for LLM generation response."""

    task: str
    result: str
