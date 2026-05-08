"""LLM-Konfiguration: Premium / Standard / Bulk Modell-Klassen.

Pro Tenant in module_parameters (module='llm', variable='{cls}_model').
Endpoints zum lesen, setzen, neueste-modelle-prüfen.
"""

from __future__ import annotations

from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.module_parameter import ModuleParameter
from app.services.llm import DEFAULT_MODELS, LLM_MODULE
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/settings/llm", tags=["settings"])


# ────────────────────────────── Schemas ──────────────────────────────


class LLMClassConfig(BaseModel):
    """One model-class entry."""

    cls: Literal["premium", "standard", "bulk"]
    model: str
    is_default: bool


class LLMSettings(BaseModel):
    premium: LLMClassConfig
    standard: LLMClassConfig
    bulk: LLMClassConfig


class LLMSettingsUpdate(BaseModel):
    premium_model: str | None = Field(default=None, max_length=100)
    standard_model: str | None = Field(default=None, max_length=100)
    bulk_model: str | None = Field(default=None, max_length=100)


class AvailableModel(BaseModel):
    id: str
    display_name: str | None = None
    suggested_class: Literal["premium", "standard", "bulk"] | None = None


# ────────────────────────────── Helpers ──────────────────────────────


CLASS_VARS = {
    "premium": "premium_model",
    "standard": "standard_model",
    "bulk": "bulk_model",
}


async def _read_value(db: AsyncSession, tenant_id: str, variable: str) -> str | None:
    result = await db.execute(
        select(ModuleParameter.value).where(
            ModuleParameter.tenant_id == tenant_id,
            ModuleParameter.module == LLM_MODULE,
            ModuleParameter.variable == variable,
        )
    )
    return result.scalar_one_or_none()


async def _write_value(
    db: AsyncSession, tenant_id: str, variable: str, value: str, description: str
) -> None:
    """Upsert a tenant-scoped LLM setting."""
    result = await db.execute(
        select(ModuleParameter).where(
            ModuleParameter.tenant_id == tenant_id,
            ModuleParameter.module == LLM_MODULE,
            ModuleParameter.variable == variable,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = ModuleParameter(
            tenant_id=tenant_id,
            module=LLM_MODULE,
            variable=variable,
            description=description,
            value=value,
            var_type="string",
            required=False,
        )
        db.add(row)
    else:
        row.value = value


def _suggest_class(model_id: str) -> Literal["premium", "standard", "bulk"] | None:
    """Heuristic - Anthropic naming gives away the tier."""
    mid = model_id.lower()
    if "opus" in mid:
        return "premium"
    if "sonnet" in mid:
        return "standard"
    if "haiku" in mid:
        return "bulk"
    return None


# ────────────────────────────── Endpoints ──────────────────────────────


@router.get("", response_model=LLMSettings)
async def get_llm_settings(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LLMSettings:
    """Aktuelle LLM-Modell-Konfiguration für den Tenant."""
    out = {}
    for cls, var in CLASS_VARS.items():
        configured = await _read_value(db, tenant_id, var)
        out[cls] = LLMClassConfig(
            cls=cls,
            model=configured or DEFAULT_MODELS[cls],
            is_default=configured is None,
        )
    return LLMSettings(**out)


@router.put("", response_model=LLMSettings)
async def update_llm_settings(
    payload: LLMSettingsUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> LLMSettings:
    """Setze ein oder mehrere Modelle für die Klassen."""
    updated_any = False
    if payload.premium_model:
        await _write_value(
            db, tenant_id, "premium_model", payload.premium_model.strip(),
            "Premium model class - interactive / setup-assistant / KI-designer",
        )
        updated_any = True
    if payload.standard_model:
        await _write_value(
            db, tenant_id, "standard_model", payload.standard_model.strip(),
            "Standard model class - body generation / personalization / replies",
        )
        updated_any = True
    if payload.bulk_model:
        await _write_value(
            db, tenant_id, "bulk_model", payload.bulk_model.strip(),
            "Bulk model class - sentiment / classification / scraping",
        )
        updated_any = True

    if updated_any:
        await db.commit()
        logger.info("LLM-Settings für Tenant {t} aktualisiert", t=tenant_id)

    return await get_llm_settings(tenant_id=tenant_id, db=db)


@router.get("/available", response_model=list[AvailableModel])
async def list_available_models(
    _tenant_id: str = Depends(get_current_tenant_id),
) -> list[AvailableModel]:
    """Liste der bei Anthropic verfügbaren Modelle (live)."""
    api_key = settings.anthropic_api_key
    if not api_key:
        raise HTTPException(
            status_code=503, detail="ANTHROPIC_API_KEY ist nicht gesetzt"
        )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Anthropic-API: {resp.status_code} - {resp.text[:200]}",
                )
            data = resp.json()
            items = data.get("data", [])
            return [
                AvailableModel(
                    id=item["id"],
                    display_name=item.get("display_name"),
                    suggested_class=_suggest_class(item["id"]),
                )
                for item in items
            ]
    except httpx.TimeoutException as e:
        raise HTTPException(status_code=504, detail="Timeout") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_available_models failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
