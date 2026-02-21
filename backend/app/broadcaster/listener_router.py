"""Listener API router - Auth, Channels, Subscriptions, Feedback, Feeds, Profile."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.broadcaster.listener_service import ListenerService
from app.broadcaster.models import ListenerUser
from app.broadcaster.schemas import (
    ChannelResponse,
    EpisodeListItem,
    EpisodeResponse,
    ExternalFeedCreate,
    ExternalFeedResponse,
    FeedbackCreate,
    FeedbackResponse,
    ListenerProfileResponse,
    LoginRequest,
    ProfileUpdate,
    RegisterRequest,
    SubscriptionCreate,
    SubscriptionResponse,
    TokenResponse,
)
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/listen", tags=["listener"])


# --- Auth Dependency ---


async def get_current_listener(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ListenerUser:
    """Extract and validate JWT from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token fehlt")
    token = auth[7:]
    service = ListenerService(db)
    try:
        return await service.get_user_from_token(token)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# --- Auth ---


@router.post("/auth/register", response_model=TokenResponse)
async def register(
    data: RegisterRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new listener user."""
    try:
        service = ListenerService(db)
        user, token = await service.register(tenant_id, data.model_dump())
        return TokenResponse(
            access_token=token,
            user=ListenerProfileResponse.model_validate(user),
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in register")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login a listener user."""
    try:
        service = ListenerService(db)
        user, token = await service.login(tenant_id, data.email, data.password)
        return TokenResponse(
            access_token=token,
            user=ListenerProfileResponse.model_validate(user),
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in login")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Channels ---


@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    tenant_id: str = Depends(get_current_tenant_id),
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelResponse]:
    """List available channels."""
    try:
        service = ListenerService(db)
        return await service.list_channels(tenant_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_channels")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/channels/{channel_id}")
async def get_channel(
    channel_id: int,
    tenant_id: str = Depends(get_current_tenant_id),
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get channel detail with episodes."""
    try:
        service = ListenerService(db)
        channel, episodes = await service.get_channel_with_episodes(
            tenant_id, channel_id
        )
        return {
            "channel": ChannelResponse.model_validate(channel),
            "episodes": [EpisodeListItem.model_validate(ep) for ep in episodes],
        }
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_channel")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Subscriptions ---


@router.get("/subscriptions", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionResponse]:
    """List user's subscriptions."""
    try:
        service = ListenerService(db)
        return await service.list_subscriptions(user)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_subscriptions")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    data: SubscriptionCreate,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    """Subscribe to a channel."""
    try:
        service = ListenerService(db)
        sub = await service.subscribe(user, data.channel_id)
        return SubscriptionResponse(
            id=sub.id,
            channel_id=sub.channel_id,
            subscribed_at=sub.subscribed_at,
        )
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in subscribe")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete(
    "/subscriptions/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsubscribe(
    channel_id: int,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unsubscribe from a channel."""
    try:
        service = ListenerService(db)
        await service.unsubscribe(user, channel_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in unsubscribe")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Feed / Episodes ---


@router.get("/feed", response_model=list[EpisodeListItem])
async def get_personal_feed(
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> list[EpisodeListItem]:
    """Get personal feed with episodes from all subscribed channels."""
    try:
        service = ListenerService(db)
        return await service.get_personal_feed(user)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_personal_feed")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: int,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> EpisodeResponse:
    """Get episode detail."""
    try:
        from app.broadcaster.service import BroadcasterService

        service = BroadcasterService(db)
        return await service.get_episode(episode_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_episode")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/episodes/{episode_id}/audio")
async def stream_audio(
    episode_id: int,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream episode audio file."""
    from pathlib import Path

    from app.broadcaster.service import BroadcasterService

    try:
        service = BroadcasterService(db)
        episode = await service.get_episode(episode_id)

        if not episode.audio_url:
            raise HTTPException(status_code=404, detail="Audio nicht verfuegbar")

        audio_path = Path(episode.audio_url)
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio-Datei nicht gefunden")

        def iterfile():
            with open(audio_path, "rb") as f:
                yield from iter(lambda: f.read(65536), b"")

        return StreamingResponse(
            iterfile(),
            media_type=episode.audio_mime_type or "audio/wav",
            headers={
                "Content-Length": str(
                    episode.audio_size_bytes or audio_path.stat().st_size
                ),
            },
        )
    except HTTPException:
        raise
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in stream_audio")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Feedback ---


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    data: FeedbackCreate,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit feedback on an episode."""
    try:
        service = ListenerService(db)
        return await service.submit_feedback(user, data.model_dump())
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in submit_feedback")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.get("/feedback/history", response_model=list[FeedbackResponse])
async def get_feedback_history(
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> list[FeedbackResponse]:
    """Get user's feedback history."""
    try:
        service = ListenerService(db)
        return await service.get_feedback_history(user)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in get_feedback_history")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- External Feeds ---


@router.get("/feeds", response_model=list[ExternalFeedResponse])
async def list_external_feeds(
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> list[ExternalFeedResponse]:
    """List user's external RSS feeds."""
    try:
        service = ListenerService(db)
        return await service.list_external_feeds(user)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in list_external_feeds")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.post(
    "/feeds",
    response_model=ExternalFeedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_external_feed(
    data: ExternalFeedCreate,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> ExternalFeedResponse:
    """Add a personal RSS feed."""
    try:
        service = ListenerService(db)
        return await service.add_external_feed(user, data.model_dump())
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in add_external_feed")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


@router.delete("/feeds/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_external_feed(
    feed_id: int,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a personal RSS feed."""
    try:
        service = ListenerService(db)
        await service.delete_external_feed(user, feed_id)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in delete_external_feed")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e


# --- Profile ---


@router.get("/profile", response_model=ListenerProfileResponse)
async def get_profile(
    user: ListenerUser = Depends(get_current_listener),
) -> ListenerProfileResponse:
    """Get current user profile."""
    return ListenerProfileResponse.model_validate(user)


@router.put("/profile", response_model=ListenerProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    user: ListenerUser = Depends(get_current_listener),
    db: AsyncSession = Depends(get_db),
) -> ListenerProfileResponse:
    """Update current user profile."""
    try:
        service = ListenerService(db)
        updated = await service.update_profile(
            user, data.model_dump(exclude_unset=True)
        )
        return ListenerProfileResponse.model_validate(updated)
    except AppError as e:
        logger.error("AppError: {msg}", msg=e.message)
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except Exception as e:
        logger.exception("Unerwarteter Fehler in update_profile")
        raise HTTPException(status_code=500, detail="Interner Serverfehler") from e
