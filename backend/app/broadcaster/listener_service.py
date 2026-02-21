"""Listener service - Auth, Subscriptions, Feedback, Personalization."""

from datetime import datetime, timedelta

import jwt
from loguru import logger
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.broadcaster.models import (
    BriefingChannel,
    BriefingEpisode,
    ListenerExternalFeed,
    ListenerFeedback,
    ListenerSubscription,
    ListenerUser,
)
from app.config import settings
from app.exceptions import AppError, DuplicateError, NotFoundError


class ListenerService:
    """Auth, subscriptions, feedback, and personalization for listener users."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Auth ---

    async def register(self, tenant_id: str, data: dict) -> tuple[ListenerUser, str]:
        """Register a new listener user. Returns (user, jwt_token)."""
        if not settings.listener_self_registration:
            raise AppError("Selbstregistrierung ist deaktiviert", 403)

        # Check duplicate
        existing = await self.db.execute(
            select(ListenerUser).where(
                ListenerUser.tenant_id == tenant_id,
                ListenerUser.email == data["email"],
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("ListenerUser", "email")

        user = ListenerUser(
            tenant_id=tenant_id,
            email=data["email"],
            password_hash=bcrypt.hash(data["password"]),
            display_name=data.get("display_name"),
            role=data.get("role"),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        token = self._create_token(user)
        logger.info(
            "Listener registriert: {email} (Tenant: {tenant})",
            email=user.email,
            tenant=tenant_id,
        )
        return user, token

    async def login(
        self, tenant_id: str, email: str, password: str
    ) -> tuple[ListenerUser, str]:
        """Authenticate a listener user. Returns (user, jwt_token)."""
        result = await self.db.execute(
            select(ListenerUser).where(
                ListenerUser.tenant_id == tenant_id,
                ListenerUser.email == email,
                ListenerUser.active.is_(True),
            )
        )
        user = result.scalar_one_or_none()
        if not user or not bcrypt.verify(password, user.password_hash):
            raise AppError("Ungueltige Zugangsdaten", 401)

        user.last_login_at = datetime.utcnow()
        await self.db.flush()

        token = self._create_token(user)
        return user, token

    def _create_token(self, user: ListenerUser) -> str:
        """Create a JWT token for a listener user."""
        payload = {
            "sub": str(user.id),
            "tenant_id": user.tenant_id,
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiry_hours),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

    async def get_user_from_token(self, token: str) -> ListenerUser:
        """Validate JWT and return user."""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as e:
            raise AppError("Token abgelaufen", 401) from e
        except jwt.InvalidTokenError as e:
            raise AppError("Ungueltiger Token", 401) from e

        user_id = int(payload["sub"])
        result = await self.db.execute(
            select(ListenerUser).where(
                ListenerUser.id == user_id,
                ListenerUser.active.is_(True),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise AppError("Benutzer nicht gefunden", 401)
        return user

    # --- Profile ---

    async def update_profile(self, user: ListenerUser, data: dict) -> ListenerUser:
        """Update listener profile."""
        for key, value in data.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # --- Channels ---

    async def list_channels(self, tenant_id: str) -> list[BriefingChannel]:
        """List available channels for a tenant."""
        result = await self.db.execute(
            select(BriefingChannel).where(
                BriefingChannel.tenant_id == tenant_id,
                BriefingChannel.active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_channel_with_episodes(
        self, tenant_id: str, channel_id: int
    ) -> tuple[BriefingChannel, list[BriefingEpisode]]:
        """Get channel detail with its episodes."""
        result = await self.db.execute(
            select(BriefingChannel).where(
                BriefingChannel.id == channel_id,
                BriefingChannel.tenant_id == tenant_id,
            )
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise NotFoundError("Channel", channel_id)

        episodes_result = await self.db.execute(
            select(BriefingEpisode)
            .where(
                BriefingEpisode.channel_id == channel_id,
                BriefingEpisode.status == "ready",
            )
            .order_by(BriefingEpisode.episode_number.desc())
        )
        episodes = list(episodes_result.scalars().all())
        return channel, episodes

    # --- Subscriptions ---

    async def list_subscriptions(self, user: ListenerUser) -> list[dict]:
        """List user's subscriptions with channel info."""
        result = await self.db.execute(
            select(ListenerSubscription, BriefingChannel)
            .join(
                BriefingChannel, ListenerSubscription.channel_id == BriefingChannel.id
            )
            .where(ListenerSubscription.user_id == user.id)
        )
        rows = result.all()
        return [
            {
                "id": sub.id,
                "channel_id": sub.channel_id,
                "channel_name": ch.name,
                "channel_slug": ch.slug,
                "subscribed_at": sub.subscribed_at,
            }
            for sub, ch in rows
        ]

    async def subscribe(
        self, user: ListenerUser, channel_id: int
    ) -> ListenerSubscription:
        """Subscribe user to a channel."""
        # Check channel exists
        ch_result = await self.db.execute(
            select(BriefingChannel).where(BriefingChannel.id == channel_id)
        )
        if not ch_result.scalar_one_or_none():
            raise NotFoundError("Channel", channel_id)

        # Check duplicate
        existing = await self.db.execute(
            select(ListenerSubscription).where(
                ListenerSubscription.user_id == user.id,
                ListenerSubscription.channel_id == channel_id,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("Subscription", "channel_id")

        sub = ListenerSubscription(
            user_id=user.id,
            channel_id=channel_id,
            subscribed_at=datetime.utcnow(),
        )
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def unsubscribe(self, user: ListenerUser, channel_id: int) -> None:
        """Unsubscribe user from a channel."""
        result = await self.db.execute(
            select(ListenerSubscription).where(
                ListenerSubscription.user_id == user.id,
                ListenerSubscription.channel_id == channel_id,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise NotFoundError("Subscription", channel_id)
        await self.db.delete(sub)
        await self.db.flush()

    # --- Feed ---

    async def get_personal_feed(self, user: ListenerUser) -> list[BriefingEpisode]:
        """Get episodes from all subscribed channels."""
        result = await self.db.execute(
            select(BriefingEpisode)
            .join(
                ListenerSubscription,
                ListenerSubscription.channel_id == BriefingEpisode.channel_id,
            )
            .where(
                ListenerSubscription.user_id == user.id,
                BriefingEpisode.status == "ready",
            )
            .order_by(BriefingEpisode.published_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    # --- Feedback ---

    async def submit_feedback(self, user: ListenerUser, data: dict) -> ListenerFeedback:
        """Submit feedback on an episode."""
        fb = ListenerFeedback(
            user_id=user.id,
            episode_id=data["episode_id"],
            finding_id=data.get("finding_id"),
            rating=data["rating"],
        )
        self.db.add(fb)
        await self.db.flush()
        await self.db.refresh(fb)

        # Update user preferences
        await self._update_preferences(user, fb)
        return fb

    async def get_feedback_history(self, user: ListenerUser) -> list[ListenerFeedback]:
        """Get user's feedback history."""
        result = await self.db.execute(
            select(ListenerFeedback)
            .where(ListenerFeedback.user_id == user.id)
            .order_by(ListenerFeedback.created_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def _update_preferences(
        self, user: ListenerUser, feedback: ListenerFeedback
    ) -> None:
        """Update user preferences based on feedback."""
        prefs = dict(user.preferences or {})
        category_weights = dict(prefs.get("category_weights", {}))

        # Get episode to find associated findings
        episode = await self.db.execute(
            select(BriefingEpisode).where(BriefingEpisode.id == feedback.episode_id)
        )
        ep = episode.scalar_one_or_none()
        if not ep or not ep.findings_used:
            return

        # Adjust weights based on rating
        weight_delta = {"interesting": 0.1, "irrelevant": -0.1, "more": 0.2}
        delta = weight_delta.get(feedback.rating, 0)

        for finding in ep.findings_used:
            # If we have finding categories, adjust those weights
            if isinstance(finding, dict):
                title = finding.get("title", "")
                keywords = prefs.get("keyword_weights", {})
                for word in title.lower().split()[:3]:
                    if len(word) > 4:
                        keywords[word] = round(keywords.get(word, 1.0) + delta, 2)
                prefs["keyword_weights"] = keywords

        prefs["category_weights"] = category_weights
        user.preferences = prefs
        await self.db.flush()

    # --- External Feeds ---

    async def list_external_feeds(
        self, user: ListenerUser
    ) -> list[ListenerExternalFeed]:
        """List user's external RSS feeds."""
        result = await self.db.execute(
            select(ListenerExternalFeed)
            .where(ListenerExternalFeed.user_id == user.id)
            .order_by(ListenerExternalFeed.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_external_feed(
        self, user: ListenerUser, data: dict
    ) -> ListenerExternalFeed:
        """Add a personal RSS feed."""
        feed = ListenerExternalFeed(
            user_id=user.id,
            name=data["name"],
            url=data["url"],
        )
        self.db.add(feed)
        await self.db.flush()
        await self.db.refresh(feed)
        return feed

    async def delete_external_feed(self, user: ListenerUser, feed_id: int) -> None:
        """Delete a personal RSS feed."""
        result = await self.db.execute(
            select(ListenerExternalFeed).where(
                ListenerExternalFeed.id == feed_id,
                ListenerExternalFeed.user_id == user.id,
            )
        )
        feed = result.scalar_one_or_none()
        if not feed:
            raise NotFoundError("ExternalFeed", feed_id)
        await self.db.delete(feed)
        await self.db.flush()
