"""Chat system schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatMessageCreate(BaseModel):
    """Create a chat message."""

    content: str


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: int
    role: str
    content: str
    metadata_: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    """Create a conversation."""

    title: str | None = None
    context_type: str = "general"
    context_data: dict | None = None


class ConversationResponse(BaseModel):
    """Conversation response with messages."""

    id: int
    title: str | None
    context_type: str
    status: str
    created_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    """Conversation list item."""

    id: int
    title: str | None
    context_type: str
    status: str
    created_at: datetime
    last_message_preview: str | None = None

    model_config = ConfigDict(from_attributes=True)
