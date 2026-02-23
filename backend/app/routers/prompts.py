"""Prompt registry router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError, DuplicateError, NotFoundError
from app.schemas.prompt import (
    PromptCreate,
    PromptListItem,
    PromptResponse,
    PromptUpdate,
)
from app.services.prompt import PromptService
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("/", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Create a new prompt template."""
    try:
        service = PromptService(db)
        return await service.create(tenant_id, data)
    except DuplicateError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/", response_model=list[PromptListItem])
async def list_prompts(
    category: str | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[PromptListItem]:
    """List prompts (deduplicated to highest version per slug)."""
    try:
        service = PromptService(db)
        return await service.list_prompts(tenant_id, category, is_active, search)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_prompts")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/slug/{slug}", response_model=PromptResponse)
async def get_prompt_by_slug(
    slug: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Get the active prompt by slug."""
    try:
        service = PromptService(db)
        return await service.get_active_by_slug(tenant_id, slug)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_prompt_by_slug")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Get a prompt by ID."""
    try:
        service = PromptService(db)
        return await service.get_by_id(tenant_id, prompt_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Update a prompt."""
    try:
        service = PromptService(db)
        return await service.update(tenant_id, prompt_id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a prompt."""
    try:
        service = PromptService(db)
        await service.delete(tenant_id, prompt_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_prompt")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/{prompt_id}/version",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    prompt_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PromptResponse:
    """Create a new version of a prompt (copy + increment version)."""
    try:
        service = PromptService(db)
        return await service.create_new_version(tenant_id, prompt_id)
    except NotFoundError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_prompt_version")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
