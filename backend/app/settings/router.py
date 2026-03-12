"""Settings API router - module and global configuration endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.settings.config_schema import GLOBAL_CATEGORIES, GLOBAL_PARAMS
from app.settings.service import SettingsService
from app.utils.dependencies import get_current_tenant_id
from app.utils.module_registry import get_all_modules, get_module

router = APIRouter(prefix="/settings", tags=["settings"])


# --- Module discovery ---


@router.get("/modules")
async def list_modules() -> list[dict]:
    """List all registered modules with metadata."""
    modules = get_all_modules()
    return [
        {
            "name": iface.MODULE_NAME,
            "label": iface.MODULE_NAME.capitalize(),
            "param_count": len(iface.PARAMS),
        }
        for iface in modules.values()
    ]


# --- Module config ---


@router.get("/modules/{name}/schema")
async def get_module_schema(name: str) -> list[dict]:
    """Return PARAMS schema for a module."""
    interface = get_module(name)
    if not interface:
        raise HTTPException(status_code=404, detail=f"Modul '{name}' nicht gefunden")
    return interface.get_config_schema()


@router.get("/modules/{name}/config")
async def get_module_config(
    name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current config for a module."""
    try:
        service = SettingsService(db)
        return await service.get_module_config(name, tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_module_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/modules/{name}/config")
async def update_module_config(
    name: str,
    updates: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update config for a module."""
    try:
        service = SettingsService(db)
        return await service.update_module_config(name, tenant_id, updates)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_module_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/modules/{name}/status")
async def get_module_status(
    name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return health status for a module."""
    try:
        service = SettingsService(db)
        return await service.get_module_status(name, tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_module_status")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Global config ---


@router.get("/global/schema")
async def get_global_schema() -> dict:
    """Return global PARAMS schema with categories."""
    return {
        "categories": GLOBAL_CATEGORIES,
        "params": GLOBAL_PARAMS,
    }


@router.get("/global/config")
async def get_global_config(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current global config (secrets redacted)."""
    try:
        service = SettingsService(db)
        return await service.get_global_config(tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_global_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/global/config")
async def update_global_config(
    updates: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update global config."""
    try:
        service = SettingsService(db)
        return await service.update_global_config(tenant_id, updates)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_global_config")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Desktop Layout ---


@router.get("/desktop-layout")
async def get_desktop_layout(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get desktop layout overrides for all modules."""
    try:
        service = SettingsService(db)
        return await service.get_desktop_layout(tenant_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_desktop_layout")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/desktop-layout/bulk-order")
async def bulk_update_desktop_order(
    order_map: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk update desktop tile order. Expects {module_name: order_int, ...}."""
    try:
        service = SettingsService(db)
        return await service.bulk_update_desktop_order(tenant_id, order_map)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_update_desktop_order")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/desktop-layout/{module_name}")
async def update_desktop_layout(
    module_name: str,
    updates: dict,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update desktop layout for a specific module."""
    try:
        service = SettingsService(db)
        return await service.update_desktop_layout(tenant_id, module_name, updates)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_desktop_layout")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/desktop-layout/{module_name}")
async def delete_desktop_override(
    module_name: str,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove all desktop overrides for a module (reset to defaults)."""
    try:
        service = SettingsService(db)
        return await service.delete_desktop_override(tenant_id, module_name)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_desktop_override")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
