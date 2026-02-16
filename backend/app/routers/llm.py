"""LLM API router."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from app.exceptions import AppError, ExternalServiceError
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.services.llm import LLMService
from app.utils.dependencies import get_tenant_config

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/generate", response_model=LLMGenerateResponse)
async def generate(
    data: LLMGenerateRequest,
    tenant_config: dict = Depends(get_tenant_config),  # noqa: B008
) -> LLMGenerateResponse:
    """Generate text using LLM with task-based model routing."""
    try:
        service = LLMService(tenant_config)
        result = await service.generate(data.task, data.prompt)
        return LLMGenerateResponse(task=data.task, result=result)
    except ExternalServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
