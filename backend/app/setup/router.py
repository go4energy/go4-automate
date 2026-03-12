"""Setup wizard API router."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.chat import (
    ChatMessageCreate,
    ConversationListItem,
    ConversationResponse,
)
from app.services.chat import ChatService
from app.setup.schemas import SetupStatusResponse
from app.setup.service import SetupAgentService
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/setup", tags=["setup"])


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_setup_conversation(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a new setup conversation."""
    try:
        service = ChatService(db)
        conversation = await service.create_conversation(tenant_id, None, "setup", None)
        await db.commit()
        return conversation
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_setup_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/conversations", response_model=list[ConversationListItem])
async def list_setup_conversations(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationListItem]:
    """List setup conversations for the current tenant."""
    try:
        service = ChatService(db)
        conversations = await service.list_conversations(tenant_id)
        # Filter to setup type only
        items = []
        for conv in conversations:
            if conv.context_type != "setup":
                continue
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
        logger.exception("Unerwarteter Fehler in list_setup_conversations")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_setup_conversation(
    conv_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Get a setup conversation with all messages."""
    try:
        service = ChatService(db)
        return await service.get_conversation(tenant_id, conv_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_setup_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setup_conversation(
    conv_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a setup conversation."""
    try:
        service = ChatService(db)
        await service.delete_conversation(tenant_id, conv_id)
        await db.commit()
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_setup_conversation")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/conversations/{conv_id}/messages")
async def send_setup_message(
    conv_id: int,
    data: ChatMessageCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Send a message and stream the setup agent response via SSE."""
    try:
        chat = ChatService(db)
        await chat.get_conversation(tenant_id, conv_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e

    service = SetupAgentService(db)

    async def event_stream():
        async for chunk in service.stream_response(
            tenant_id, conv_id, data.content, tenant_config
        ):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current setup progress."""
    try:
        service = SetupAgentService(db)
        return await service.get_setup_progress(tenant_id, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_setup_status")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
