"""Broadcaster Admin API router."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.broadcaster.config_schema import broadcaster_interface
from app.broadcaster.schemas import (
    ChannelCreate,
    ChannelResponse,
    ChannelUpdate,
    EpisodeListItem,
    EpisodeResponse,
    ListenerUserCreate,
    ListenerUserResponse,
)
from app.broadcaster.service import BroadcasterService
from app.config import settings
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id, get_tenant_config

router = APIRouter(prefix="/broadcaster", tags=["broadcaster"])

# Register standardized module interface endpoints
broadcaster_interface.register_endpoints(router)


# --- Channels ---


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelResponse]:
    """List all briefing channels."""
    try:
        service = BroadcasterService(db)
        return await service.list_channels(tenant_id)
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Create a new briefing channel."""
    try:
        service = BroadcasterService(db)
        return await service.create_channel(tenant_id, data.model_dump())
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in create_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Get a single briefing channel."""
    try:
        service = BroadcasterService(db)
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ChannelResponse:
    """Update a briefing channel."""
    try:
        service = BroadcasterService(db)
        channel = await service.update_channel(
            tenant_id, channel_id, data.model_dump(exclude_unset=True)
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a briefing channel."""
    try:
        service = BroadcasterService(db)
        await service.delete_channel(tenant_id, channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_channel")
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
        service = BroadcasterService(db)
        return await service.list_episodes(channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_episodes")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/channels/{channel_id}/generate",
    response_model=EpisodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_episode(
    channel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_config: dict = Depends(get_tenant_config),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    """Generate a new episode for a channel."""
    try:
        service = BroadcasterService(db)
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
        service = BroadcasterService(db)
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
        service = BroadcasterService(db)
        await service.delete_episode(episode_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_episode")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Listener User Management (Admin) ---


@router.get("/users", response_model=list[ListenerUserResponse])
async def list_users(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ListenerUserResponse]:
    """List all listener users."""
    try:
        service = BroadcasterService(db)
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ListenerUserResponse:
    """Create a listener user."""
    try:
        service = BroadcasterService(db)
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
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a listener user."""
    try:
        service = BroadcasterService(db)
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

    from app.broadcaster.feed import generate_feed
    from app.broadcaster.models import BriefingChannel, BriefingEpisode

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
