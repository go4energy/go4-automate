"""Briefing Admin API router."""

from pathlib import Path

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.briefing.config_schema import briefing_interface
from app.briefing.schemas import (
    BriefingAccountConnectionResponse,
    BriefingFindingResponse,
    BriefingFindingUpdate,
    BriefingPersonalSettingsResponse,
    BriefingPersonalSettingsUpdate,
    BriefingRunResponse,
    BriefingSourceCreate,
    BriefingSourceResponse,
    BriefingSourceUpdate,
    BulkDeleteRequest,
    BulkDeleteResponse,
    ChannelCloneRequest,
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    EpisodeListItem,
    EpisodeResponse,
    ListenerUserCreate,
    ListenerUserResponse,
    SpeakerResponse,
)
from app.briefing.service import BriefingService
from app.config import settings
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/briefing", tags=["briefing"])

# Register standardized module interface endpoints
briefing_interface.register_endpoints(router)


def _is_admin(user: User) -> bool:
    """Check if user has admin role."""
    return user.role == "admin"


def _user_id_for_create(user: User, org_wide: bool) -> int | None:
    """Determine user_id for resource creation. Org-wide only for admins."""
    if org_wide and _is_admin(user):
        return None
    return user.id


async def _fetch_available_ollama_models() -> list[str]:
    """Read installed Ollama models from the configured Ollama server."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Ollama model list could not be loaded: {error}", error=str(exc))
        return []

    payload = response.json()
    models = payload.get("models", [])
    excluded_keywords = (
        "embed",
        "embedding",
        "bge",
        "mxbai",
        "vision",
        "llava",
        "minicpm-v",
        "vde",
    )
    names = []
    for item in models:
        name = item.get("name")
        if isinstance(name, str) and name:
            lowered = name.lower()
            if any(keyword in lowered for keyword in excluded_keywords):
                continue
            names.append(name)
    return sorted(set(names))


def _oauth_scope(provider: str, integration_type: str | None = None) -> str:
    """Return provider scopes. Delegates to shared layer."""
    from app.integrations.oauth import oauth_scope

    return oauth_scope(provider, integration_type)


def _build_oauth_auth_url(
    provider: str,
    state: str,
    callback_url: str,
    integration_type: str | None = None,
) -> str:
    """Build the provider-specific OAuth authorization URL."""
    from urllib.parse import quote, urlencode

    scope = _oauth_scope(provider, integration_type)

    if provider == "microsoft":
        tid = settings.microsoft_tenant_id or "common"
        params = urlencode(
            {
                "client_id": settings.microsoft_client_id,
                "response_type": "code",
                "redirect_uri": callback_url,
                "scope": scope,
                "state": state,
            },
            quote_via=quote,
        )
        return f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/authorize?{params}"

    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "response_type": "code",
            "redirect_uri": callback_url,
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        },
        quote_via=quote,
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


async def _exchange_oauth_code(
    code: str,
    provider: str,
    callback_url: str,
    integration_type: str | None = None,
) -> dict:
    """Exchange an OAuth code for tokens. Delegates to shared layer."""
    from app.integrations.oauth import exchange_oauth_code

    return await exchange_oauth_code(code, provider, callback_url, integration_type)


async def _fetch_oauth_email(access_token: str, provider: str) -> str:
    """Fetch primary email. Delegates to shared layer."""
    from app.integrations.oauth import fetch_oauth_email

    return await fetch_oauth_email(access_token, provider)


def _extract_token_scopes(tokens: dict) -> list[str]:
    """Normalize returned scopes from OAuth providers."""
    scope = tokens.get("scope")
    if isinstance(scope, str):
        return [item for item in scope.split() if item]
    if isinstance(scope, list):
        return [str(item) for item in scope if item]
    return []


# --- Channels ---


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelResponse]:
    """List briefing channels visible to user (org + personal)."""
    try:
        service = BriefingService(db)
        return await service.list_channels(tenant_id, user.id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_channels")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/channels",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    data: ChannelCreate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    org_wide: bool = Query(False),
) -> ChannelResponse:
    """Create a new briefing channel. org_wide=true requires admin."""
    try:
        service = BriefingService(db)
        uid = _user_id_for_create(user, org_wide)
        return await service.create_channel(tenant_id, data.model_dump(), uid)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Get a single briefing channel."""
    try:
        service = BriefingService(db)
        return await service.get_channel(tenant_id, channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    data: ChannelUpdate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Update a briefing channel."""
    try:
        service = BriefingService(db)
        channel = await service.update_channel(
            tenant_id,
            channel_id,
            data.model_dump(exclude_unset=True),
            user_id=user.id,
            is_admin=_is_admin(user),
        )
        result = channel.__dict__.copy()
        result["episode_count"] = await service._count_episodes(channel.id)
        result["subscriber_count"] = await service._count_subscribers(channel.id)
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a briefing channel."""
    try:
        service = BriefingService(db)
        await service.delete_channel(
            tenant_id, channel_id, user_id=user.id, is_admin=_is_admin(user)
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Channel Clone ---


@router.post(
    "/channels/{channel_id}/clone",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_channel(
    channel_id: int,
    data: ChannelCloneRequest,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Clone an org channel as a personal channel."""
    try:
        service = BriefingService(db)
        channel = await service.clone_channel(
            tenant_id, channel_id, user.id, data.model_dump(exclude_unset=True)
        )
        result = channel.__dict__.copy()
        result["episode_count"] = 0
        result["subscriber_count"] = 0
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in clone_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Channel-Source Linking ---


@router.post(
    "/channels/{channel_id}/sources/{source_id}",
    status_code=status.HTTP_201_CREATED,
)
async def link_source_to_channel(
    channel_id: int,
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Link a source to a channel."""
    try:
        service = BriefingService(db)
        link = await service.link_source_to_channel(tenant_id, channel_id, source_id)
        return {"channel_id": link.channel_id, "source_id": link.source_id}
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in link_source_to_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/channels/{channel_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_source_from_channel(
    channel_id: int,
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unlink a source from a channel."""
    try:
        service = BriefingService(db)
        await service.unlink_source_from_channel(tenant_id, channel_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in unlink_source_from_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get(
    "/channels/{channel_id}/sources",
    response_model=list[BriefingSourceResponse],
)
async def list_channel_sources(
    channel_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[BriefingSourceResponse]:
    """List sources linked to a channel."""
    try:
        service = BriefingService(db)
        return await service.list_channel_sources(tenant_id, channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_channel_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Sources ---


@router.get("/sources", response_model=list[BriefingSourceResponse])
async def list_sources(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    source_type: str | None = Query(None),
    active: bool | None = Query(None),
) -> list[BriefingSourceResponse]:
    """List briefing sources visible to user (org + personal)."""
    try:
        service = BriefingService(db)
        return await service.list_sources(
            tenant_id, source_type, active, user_id=user.id
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/sources",
    response_model=BriefingSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    data: BriefingSourceCreate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    org_wide: bool = Query(False),
) -> BriefingSourceResponse:
    """Create a new briefing source. org_wide=true requires admin."""
    try:
        service = BriefingService(db)
        uid = _user_id_for_create(user, org_wide)
        return await service.create_source(tenant_id, data.model_dump(), uid)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/sources/run", response_model=BriefingRunResponse)
async def run_sources(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingRunResponse:
    """Run all due briefing sources."""
    try:
        service = BriefingService(db)
        return await service.run_sources(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_sources")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/sources/{source_id}", response_model=BriefingSourceResponse)
async def get_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingSourceResponse:
    """Get a single briefing source."""
    try:
        service = BriefingService(db)
        return await service.get_source(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/sources/{source_id}", response_model=BriefingSourceResponse)
async def update_source(
    source_id: int,
    data: BriefingSourceUpdate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingSourceResponse:
    """Update a briefing source."""
    try:
        service = BriefingService(db)
        return await service.update_source(
            tenant_id,
            source_id,
            data.model_dump(exclude_unset=True),
            user_id=user.id,
            is_admin=_is_admin(user),
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a briefing source."""
    try:
        service = BriefingService(db)
        await service.delete_source(
            tenant_id, source_id, user_id=user.id, is_admin=_is_admin(user)
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/sources/{source_id}/run", response_model=BriefingRunResponse)
async def run_single_source(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingRunResponse:
    """Run a single briefing source."""
    try:
        service = BriefingService(db)
        return await service.run_sources(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_single_source")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Personal Briefing ---


@router.get(
    "/personal/settings", response_model=BriefingPersonalSettingsResponse
)
async def get_personal_settings(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingPersonalSettingsResponse:
    """Return the user's personal morning briefing settings."""
    try:
        service = BriefingService(db)
        return await service.get_personal_settings(tenant_id, user.id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_personal_settings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put(
    "/personal/settings", response_model=BriefingPersonalSettingsResponse
)
async def update_personal_settings(
    data: BriefingPersonalSettingsUpdate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingPersonalSettingsResponse:
    """Update the user's personal morning briefing settings."""
    try:
        service = BriefingService(db)
        return await service.update_personal_settings(
            tenant_id,
            user.id,
            data.model_dump(exclude_unset=True),
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_personal_settings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get(
    "/personal/connections", response_model=list[BriefingAccountConnectionResponse]
)
async def list_personal_connections(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[BriefingAccountConnectionResponse]:
    """List the user's personal email/calendar integrations."""
    try:
        service = BriefingService(db)
        return await service.list_personal_connections(tenant_id, user.id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_personal_connections")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/personal/admin/ollama-models")
async def list_available_ollama_models(
    user: User = Depends(get_current_user),
):
    """Return locally available Ollama models for admin configuration."""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail="Nur Administratoren haben Zugriff")
    return {"models": await _fetch_available_ollama_models()}


@router.get("/personal/oauth/authorize")
async def personal_oauth_authorize(
    provider: str = Query(..., pattern=r"^(microsoft|google)$"),
    integration_type: str = Query(..., pattern=r"^(email|calendar)$"),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Return the OAuth URL for a personal email or calendar integration."""
    from app.briefing.oauth import encrypt_token

    try:
        state = encrypt_token(
            {
                "tenant_id": tenant_id,
                "user_id": user.id,
                "provider": provider,
                "integration_type": integration_type,
                "flow": "personal",
            }
        )
        callback_url = f"{settings.app_url}/api/v1/briefing/personal/oauth/callback"
        return {
            "auth_url": _build_oauth_auth_url(
                provider,
                state,
                callback_url,
                integration_type=integration_type,
            )
        }
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in personal_oauth_authorize")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/personal/oauth/callback")
async def personal_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """OAuth callback for personal email/calendar integrations."""
    from datetime import datetime

    from fastapi.responses import HTMLResponse

    from app.briefing.oauth import decrypt_token, encrypt_token

    try:
        state_data = decrypt_token(state)
        tenant_id = state_data["tenant_id"]
        user_id = state_data["user_id"]
        provider = state_data["provider"]
        integration_type = state_data["integration_type"]

        callback_url = f"{settings.app_url}/api/v1/briefing/personal/oauth/callback"
        tokens = await _exchange_oauth_code(
            code,
            provider,
            callback_url,
            integration_type=integration_type,
        )
        email = await _fetch_oauth_email(tokens["access_token"], provider)

        token_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": datetime.utcnow().timestamp()
            + tokens.get("expires_in", 3600),
        }

        service = BriefingService(db)
        await service.upsert_personal_connection(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            integration_type=integration_type,
            encrypted_token=encrypt_token(token_data),
            connected_email=email,
            scopes=_extract_token_scopes(tokens),
        )
        await db.commit()

        logger.info(
            "Persoenliche OAuth-Verbindung erstellt: user={user_id} provider={provider} type={integration_type}",
            user_id=user_id,
            provider=provider,
            integration_type=integration_type,
        )
        return HTMLResponse(OAUTH_CALLBACK_HTML)
    except Exception as e:
        logger.exception("Personal OAuth callback Fehler")
        error_msg = str(e)[:200]
        return HTMLResponse(OAUTH_ERROR_HTML % (error_msg, error_msg), status_code=400)


@router.post(
    "/personal/connections/{connection_id}/disconnect",
    response_model=BriefingAccountConnectionResponse,
)
async def disconnect_personal_connection(
    connection_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingAccountConnectionResponse:
    """Disconnect a personal email/calendar integration."""
    try:
        service = BriefingService(db)
        return await service.disconnect_personal_connection(
            tenant_id,
            connection_id,
            current_user_id=user.id,
            is_admin=_is_admin(user),
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in disconnect_personal_connection")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/personal/run")
async def run_personal_briefing(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a manual personal morning briefing fetch for the current user."""
    try:
        service = BriefingService(db)
        result = await service.run_personal_briefing(tenant_id, user.id)
        await db.commit()
        return result
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in run_personal_briefing")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Findings ---


@router.get("/findings", response_model=list[BriefingFindingResponse])
async def list_findings(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status"),
    source_id: int | None = Query(None),
    source_type: str | None = Query(None),
) -> list[BriefingFindingResponse]:
    """List briefing findings visible to user."""
    try:
        service = BriefingService(db)
        return await service.list_findings(
            tenant_id, status_filter, source_id, source_type, user_id=user.id
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_findings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.put("/findings/{finding_id}", response_model=BriefingFindingResponse)
async def update_finding(
    finding_id: int,
    data: BriefingFindingUpdate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingFindingResponse:
    """Update a briefing finding."""
    try:
        service = BriefingService(db)
        return await service.update_finding(
            tenant_id, finding_id, data.model_dump(exclude_unset=True)
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_finding")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/findings/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_findings(
    data: BulkDeleteRequest,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkDeleteResponse:
    """Bulk delete briefing findings."""
    try:
        service = BriefingService(db)
        deleted = await service.bulk_delete_findings(tenant_id, data.ids)
        return BulkDeleteResponse(deleted=deleted)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in bulk_delete_findings")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Episodes ---


@router.get(
    "/channels/{channel_id}/episodes",
    response_model=list[EpisodeListItem],
)
async def list_episodes(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[EpisodeListItem]:
    """List episodes for a channel."""
    try:
        service = BriefingService(db)
        return await service.list_episodes(channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_episodes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Episode Generation ---


@router.post(
    "/channels/{channel_id}/generate",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_episode(
    channel_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    """Generate a new episode for a channel."""
    try:
        service = BriefingService(db)
        return await service.generate_episode(tenant_id, channel_id, tenant_config)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in generate_episode")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: int,
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    """Get a single episode."""
    try:
        service = BriefingService(db)
        return await service.get_episode(episode_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_episode")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/episodes/{episode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_episode(
    episode_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an episode."""
    try:
        service = BriefingService(db)
        await service.delete_episode(episode_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_episode")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Listener User Management (Deprecated — kept for backward compat) ---


@router.get("/users", response_model=list[ListenerUserResponse])
async def list_users(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ListenerUserResponse]:
    """List all listener users (deprecated)."""
    try:
        service = BriefingService(db)
        return await service.list_users(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_users")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/users",
    response_model=ListenerUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: ListenerUserCreate,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ListenerUserResponse:
    """Create a listener user (deprecated)."""
    try:
        service = BriefingService(db)
        return await service.create_user(tenant_id, data.model_dump())
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a listener user (deprecated)."""
    try:
        service = BriefingService(db)
        await service.delete_user(tenant_id, user_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_user")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Public Feed ---


@router.get("/feed/{tenant_id}/{slug}/feed.xml")
async def get_feed(
    tenant_id: str,
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Public RSS feed for a channel (no auth required)."""
    from sqlalchemy import select

    from app.briefing.feed import generate_feed
    from app.briefing.models import BriefingChannel, BriefingEpisode

    try:
        result = await db.execute(
            select(BriefingChannel).where(
                BriefingChannel.tenant_id == tenant_id,
                BriefingChannel.slug == slug,
            )
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel nicht gefunden")

        episodes_result = await db.execute(
            select(BriefingEpisode)
            .where(BriefingEpisode.channel_id == channel.id)
            .order_by(BriefingEpisode.episode_number.desc())
            .limit(50)
        )
        episodes = list(episodes_result.scalars().all())

        base_url = f"https://{settings.domain}"
        xml = generate_feed(channel, episodes, base_url)

        return Response(content=xml, media_type="application/rss+xml")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_feed")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Speakers (XTTS Voice Cloning) ---


@router.get("/speakers", response_model=list[SpeakerResponse])
async def list_speakers(
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[SpeakerResponse]:
    """List all speakers for the tenant."""
    try:
        service = BriefingService(db)
        return await service.list_speakers(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_speakers")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/speakers", response_model=SpeakerResponse, status_code=status.HTTP_201_CREATED
)
async def upload_speaker(
    name: str = Form(...),
    language: str = Form("de"),
    description: str = Form(None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SpeakerResponse:
    """Upload a WAV file as a new speaker voice."""
    if not _is_admin(user):
        raise HTTPException(
            status_code=403, detail="Nur Admins koennen Speaker verwalten"
        )

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Nur WAV-Dateien erlaubt")

    file_bytes = await file.read()

    # Validate file size (max 10 MB)
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Datei zu gross (max 10 MB)")

    try:
        service = BriefingService(db)
        return await service.create_speaker(
            tenant_id, name, language, file_bytes, description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in upload_speaker")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/speakers/{speaker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_speaker(
    speaker_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a speaker and its files."""
    if not _is_admin(user):
        raise HTTPException(
            status_code=403, detail="Nur Admins koennen Speaker verwalten"
        )

    try:
        service = BriefingService(db)
        await service.delete_speaker(tenant_id, speaker_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_speaker")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/speakers/{speaker_id}/preview")
async def preview_speaker(
    speaker_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Stream the speaker's WAV sample for preview."""
    try:
        service = BriefingService(db)
        speaker = await service.get_speaker(tenant_id, speaker_id)
        file_path = Path(speaker.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Audio-Datei nicht gefunden")
        audio_bytes = file_path.read_bytes()
        return Response(content=audio_bytes, media_type="audio/wav")
    except HTTPException:
        raise
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in preview_speaker")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- OAuth (Calendar/Email Sources) ---


OAUTH_CALLBACK_HTML = """<!DOCTYPE html>
<html><body><script>
window.opener?.postMessage({type:'oauth_success'}, '*');
window.close();
</script><p>Verbindung erfolgreich. Dieses Fenster kann geschlossen werden.</p></body></html>"""

OAUTH_ERROR_HTML = """<!DOCTYPE html>
<html><body><script>
window.opener?.postMessage({type:'oauth_error', error:'%s'}, '*');
window.close();
</script><p>Fehler: %s</p></body></html>"""


@router.get("/oauth/authorize")
async def oauth_authorize(
    source_id: int = Query(...),
    provider: str = Query(..., pattern=r"^(microsoft|google)$"),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """Return OAuth auth URL for the given provider."""
    from urllib.parse import quote, urlencode

    from app.briefing.oauth import encrypt_token

    try:
        service = BriefingService(db)
        await service.get_source(tenant_id, source_id, raw=True)

        state = encrypt_token(
            {
                "source_id": source_id,
                "tenant_id": tenant_id,
                "user_id": user.id,
                "provider": provider,
            }
        )

        callback_url = f"{settings.app_url}/api/v1/briefing/oauth/callback"

        if provider == "microsoft":
            tid = settings.microsoft_tenant_id or "common"
            params = urlencode(
                {
                    "client_id": settings.microsoft_client_id,
                    "response_type": "code",
                    "redirect_uri": callback_url,
                    "scope": "Calendars.Read Mail.Read User.Read offline_access",
                    "state": state,
                },
                quote_via=quote,
            )
            auth_url = f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/authorize?{params}"
        else:
            params = urlencode(
                {
                    "client_id": settings.google_client_id,
                    "response_type": "code",
                    "redirect_uri": callback_url,
                    "scope": (
                        "https://www.googleapis.com/auth/calendar.readonly "
                        "https://www.googleapis.com/auth/gmail.readonly "
                        "openid email"
                    ),
                    "access_type": "offline",
                    "prompt": "consent",
                    "state": state,
                },
                quote_via=quote,
            )
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

        return {"auth_url": auth_url}
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in oauth_authorize")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """OAuth callback: exchange code for tokens, store in source config."""
    from datetime import datetime

    from fastapi.responses import HTMLResponse

    from app.briefing.oauth import decrypt_token, encrypt_token

    try:
        state_data = decrypt_token(state)
        source_id = state_data["source_id"]
        tenant_id = state_data["tenant_id"]
        provider = state_data["provider"]

        callback_url = f"{settings.app_url}/api/v1/briefing/oauth/callback"

        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            # Exchange code for tokens
            if provider == "microsoft":
                tid = settings.microsoft_tenant_id or "common"
                token_resp = await client.post(
                    f"https://login.microsoftonline.com/{tid}/oauth2/v2.0/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": settings.microsoft_client_id,
                        "client_secret": settings.microsoft_client_secret,
                        "code": code,
                        "redirect_uri": callback_url,
                        "scope": "Calendars.Read Mail.Read User.Read offline_access",
                    },
                )
            else:
                token_resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "code": code,
                        "redirect_uri": callback_url,
                    },
                )

            token_resp.raise_for_status()
            tokens = token_resp.json()

            # Get user email
            access_token = tokens["access_token"]
            if provider == "microsoft":
                me_resp = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                me_resp.raise_for_status()
                me = me_resp.json()
                email = me.get("mail") or me.get("userPrincipalName", "")
            else:
                me_resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                me_resp.raise_for_status()
                email = me_resp.json().get("email", "")

        # Store encrypted tokens in source config
        from sqlalchemy import select

        from app.briefing.models import BriefingSource

        result = await db.execute(
            select(BriefingSource).where(
                BriefingSource.id == source_id,
                BriefingSource.tenant_id == tenant_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            return HTMLResponse(OAUTH_ERROR_HTML % ("Source nicht gefunden",) * 2, 400)

        token_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": datetime.utcnow().timestamp()
            + tokens.get("expires_in", 3600),
        }

        cfg = source.config or {}
        cfg["oauth_provider"] = provider
        cfg["oauth_token"] = encrypt_token(token_data)
        cfg["oauth_email"] = email
        cfg["oauth_connected_at"] = datetime.utcnow().isoformat()
        source.config = cfg
        await db.commit()

        logger.info(
            "OAuth verbunden: Source {sid} via {provider} ({email})",
            sid=source_id,
            provider=provider,
            email=email,
        )

        return HTMLResponse(OAUTH_CALLBACK_HTML)

    except Exception as e:
        logger.exception("OAuth callback Fehler")
        error_msg = str(e)[:200]
        return HTMLResponse(OAUTH_ERROR_HTML % (error_msg, error_msg), status_code=400)


@router.post("/sources/{source_id}/oauth/disconnect")
async def oauth_disconnect(
    source_id: int,
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BriefingSourceResponse:
    """Remove OAuth connection from a source."""
    try:
        service = BriefingService(db)
        return await service.disconnect_oauth(tenant_id, source_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in oauth_disconnect")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
