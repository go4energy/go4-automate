"""LLM API router."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import (
    AppError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from app.schemas.llm import LLMGenerateRequest, LLMGenerateResponse
from app.schemas.prompt import PromptExecuteRequest, PromptExecuteResponse
from app.services.llm import LLMService
from app.services.prompt import PromptService
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

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


@router.post("/execute", response_model=PromptExecuteResponse)
async def execute_prompt(
    data: PromptExecuteRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PromptExecuteResponse:
    """Execute a prompt from the registry by slug. Used by n8n workflows."""
    try:
        service = PromptService(db)
        result = await service.execute(tenant_id, data, tenant_config)
        return PromptExecuteResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ValidationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except ExternalServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in execute_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
