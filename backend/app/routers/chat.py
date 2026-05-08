"""Chat API router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.chat import (
    ChatMessageCreate,
    ConversationCreate,
    ConversationListItem,
    ConversationResponse,
    TopicInfo,
)
from app.services.chat import ChatService
from app.services.chat_topics import list_topics
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/topics", response_model=list[TopicInfo])
async def get_topics() -> list[TopicInfo]:
    """List all registered help topics. Frontend uses this to map topic-IDs
    declared by views to titles for the chat-panel suggestions."""
    return [TopicInfo(**t) for t in list_topics()]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    data: ConversationCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a new conversation."""
    try:
        service = ChatService(db)
        # Topic-tagged: reuse an existing active conversation for the same
        # topic so the help thread stays continuous instead of fragmenting.
        if data.topic:
            existing = await service.find_topic_conversation(tenant_id, data.topic)
            if existing:
                # Refresh context_data so the latest form-state is used.
                if data.context_data:
                    existing.context_data = data.context_data
                    await db.commit()
                return existing
        conversation = await service.create_conversation(
            tenant_id,
            data.title,
            data.context_type,
            data.context_data,
            topic=data.topic,
        )
        await db.commit()
        return conversation
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_conversations(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
) -> list[ConversationListItem]:
    """List conversations for the current tenant."""
    try:
        service = ChatService(db)
        conversations = await service.list_conversations(
            tenant_id, status=status_filter
        )
        # Build list items with last message preview
        items = []
        for conv in conversations:
            preview = None
            if conv.messages:
                last = conv.messages[-1]
                preview = last.content[:100] + (
                    "..." if len(last.content) > 100 else ""
                )
            items.append(
                ConversationListItem(
                    id=conv.id,
                    title=conv.title,
                    context_type=conv.context_type,
                    topic=conv.topic,
                    status=conv.status,
                    created_at=conv.created_at,
                    last_message_preview=preview,
                )
            )
        return items
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_conversations")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get a conversation with all messages."""
    try:
        service = ChatService(db)
        return await service.get_conversation(tenant_id, conv_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conv_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a conversation and all its messages."""
    try:
        service = ChatService(db)
        await service.delete_conversation(tenant_id, conv_id)
        await db.commit()
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/conversations/{conv_id}/messages")
async def send_message(
    conv_id: int,
    data: ChatMessageCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Send a message and stream the assistant response via SSE."""
    try:
        service = ChatService(db)
        # Verify conversation exists
        await service.get_conversation(tenant_id, conv_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    async def event_stream():
        async for chunk in service.stream_response(
            tenant_id, conv_id, data.content, tenant_config
        ):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")
