"""KI-Chat endpoints — per template designer-assistant chat."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.emailmarketing.ai_chat_service import AiChatService
from app.emailmarketing.schemas import (
    AiChatMessage,
    AiChatSendRequest,
    AiChatSendResponse,
    AiChatToolCall,
)
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(
    prefix="/emailmarketing/templates", tags=["emailmarketing"]
)


@router.get("/{template_id}/ai-chat", response_model=list[AiChatMessage])
async def get_chat_history(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[AiChatMessage]:
    service = AiChatService(db)
    rows = await service.get_history(tenant_id, template_id)
    return [AiChatMessage.model_validate(r) for r in rows]


@router.post("/{template_id}/ai-chat", response_model=AiChatSendResponse)
async def send_chat_message(
    template_id: int,
    payload: AiChatSendRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AiChatSendResponse:
    service = AiChatService(db)
    try:
        result = await service.send_message(
            tenant_id,
            template_id,
            payload.message,
            current_html=payload.current_html,
        )
        await db.commit()
        return AiChatSendResponse(
            assistant_message=AiChatMessage.model_validate(result["assistant_message"]),
            tool_calls=[AiChatToolCall(**tc) for tc in result["tool_calls"]],
            new_html=result["new_html"],
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        await db.rollback()
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        logger.exception("AI chat failed")
        raise HTTPException(status_code=500, detail="KI-Chat fehlgeschlagen") from e


@router.delete(
    "/{template_id}/ai-chat",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def clear_chat_history(
    template_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    service = AiChatService(db)
    await service.clear_history(tenant_id, template_id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
