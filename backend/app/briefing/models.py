"""Briefing models - Channel, Episode, Source, Finding, ListenerUser, Subscription, Feedback, ExternalFeed."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class BriefingSource(TimestampMixin, Base):
    """A data source for the briefing module (RSS, website, calendar, email, KPI, websearch)."""

    __tablename__ = "briefing_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fetch_interval_hours: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column()
    config: Mapped[dict | None] = mapped_column(JSONB)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    streams: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Relationships
    tenant = relationship("Tenant")
    findings = relationship(
        "BriefingFinding", back_populates="source", cascade="all, delete-orphan"
    )
    channel_links = relationship(
        "BriefingChannelSource", back_populates="source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_briefing_sources_tenant_active", "tenant_id", "active"),
        Index("ix_briefing_sources_tenant_type", "tenant_id", "source_type"),
        Index("ix_briefing_sources_tenant_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BriefingSource {self.name!r} ({self.source_type})>"


class BriefingFinding(TimestampMixin, Base):
    """A finding discovered by a briefing source."""

    __tablename__ = "briefing_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("briefing_sources.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    content_snippet: Mapped[str | None] = mapped_column(Text)
    found_at: Mapped[datetime] = mapped_column(nullable=False)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(30))
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    streams: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    # Relationships
    source = relationship("BriefingSource", back_populates="findings")

    __table_args__ = (
        UniqueConstraint("tenant_id", "url", name="uq_briefing_findings_tenant_url"),
        Index("ix_briefing_findings_tenant_status", "tenant_id", "status"),
        Index("ix_briefing_findings_tenant_source", "tenant_id", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<BriefingFinding {self.title!r} ({self.status})>"


class BriefingChannelSource(Base):
    """Many-to-many link between channels and sources."""

    __tablename__ = "briefing_channel_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_channels.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_sources.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    channel = relationship("BriefingChannel", back_populates="source_links")
    source = relationship("BriefingSource", back_populates="channel_links")

    __table_args__ = (
        UniqueConstraint(
            "channel_id", "source_id", name="uq_briefing_channel_sources_channel_source"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<BriefingChannelSource channel={self.channel_id} source={self.source_id}>"
        )


class BriefingSpeaker(TimestampMixin, Base):
    """A voice speaker for XTTS v2 voice cloning."""

    __tablename__ = "briefing_speakers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10), default="de", nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    xtts_speaker_name: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_briefing_speakers_tenant_name"),
        Index("ix_briefing_speakers_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<BriefingSpeaker {self.name!r} ({self.language})>"


class BriefingChannel(TimestampMixin, Base):
    """A briefing channel targeting a specific audience."""

    __tablename__ = "briefing_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    cloned_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("briefing_channels.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(String(200))
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)
    streams: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(50))
    voice: Mapped[str] = mapped_column(
        String(100), default="de_DE-thorsten-high", nullable=False
    )
    language: Mapped[str] = mapped_column(String(10), default="de", nullable=False)
    intro_text: Mapped[str | None] = mapped_column(Text)
    outro_text: Mapped[str | None] = mapped_column(Text)
    personal_context_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    max_items: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_duration_minutes: Mapped[int] = mapped_column(
        Integer, default=5, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    output_format: Mapped[str] = mapped_column(
        String(20), default="audio", nullable=False
    )
    text_format: Mapped[str] = mapped_column(
        String(20), default="markdown", nullable=False
    )
    tts_engine: Mapped[str | None] = mapped_column(String(20), nullable=True)
    xtts_speaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("briefing_speakers.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant = relationship("Tenant")
    episodes = relationship(
        "BriefingEpisode", back_populates="channel", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "ListenerSubscription", back_populates="channel", cascade="all, delete-orphan"
    )
    source_links = relationship(
        "BriefingChannelSource", back_populates="channel", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Partial unique indexes on slug are defined in migration 020
        Index("ix_briefing_channels_tenant", "tenant_id"),
        Index("ix_briefing_channels_tenant_user", "tenant_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BriefingChannel {self.name!r} ({self.slug})>"


class BriefingEpisode(TimestampMixin, Base):
    """A single generated episode of a briefing channel."""

    __tablename__ = "briefing_episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_channels.id", ondelete="CASCADE"), nullable=False
    )
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(String(500))
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    audio_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    audio_mime_type: Mapped[str] = mapped_column(
        String(50), default="audio/wav", nullable=False
    )
    findings_used: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(20), default="generating", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    text_content: Mapped[str | None] = mapped_column(Text)
    output_format: Mapped[str] = mapped_column(
        String(20), default="audio", nullable=False
    )
    generated_at: Mapped[datetime | None] = mapped_column()
    published_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    channel = relationship("BriefingChannel", back_populates="episodes")
    feedback = relationship(
        "ListenerFeedback", back_populates="episode", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_briefing_episodes_channel", "channel_id", "published_at"),
        Index("ix_briefing_episodes_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<BriefingEpisode #{self.episode_number} ({self.status})>"


class ListenerUser(TimestampMixin, Base):
    """An end-user of the Listener PWA."""

    __tablename__ = "listener_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("tenants.tenant_id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(50))
    preferences: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    personal_webhook_url: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    subscriptions = relationship(
        "ListenerSubscription", back_populates="user", cascade="all, delete-orphan"
    )
    feedback = relationship(
        "ListenerFeedback", back_populates="user", cascade="all, delete-orphan"
    )
    external_feeds = relationship(
        "ListenerExternalFeed", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_listener_users_tenant_email"),
        Index("ix_listener_users_email", "tenant_id", "email"),
    )

    def __repr__(self) -> str:
        return f"<ListenerUser {self.email!r}>"


class ListenerSubscription(TimestampMixin, Base):
    """A user's subscription to a briefing channel."""

    __tablename__ = "listener_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("listener_users.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_channels.id", ondelete="CASCADE"), nullable=False
    )
    subscribed_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    user = relationship("ListenerUser", back_populates="subscriptions")
    channel = relationship("BriefingChannel", back_populates="subscriptions")

    __table_args__ = (
        UniqueConstraint(
            "user_id", "channel_id", name="uq_listener_subscriptions_user_channel"
        ),
    )

    def __repr__(self) -> str:
        return f"<ListenerSubscription user={self.user_id} channel={self.channel_id}>"


class ListenerFeedback(TimestampMixin, Base):
    """User feedback on an episode segment."""

    __tablename__ = "listener_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("listener_users.id", ondelete="CASCADE"), nullable=False
    )
    episode_id: Mapped[int] = mapped_column(
        ForeignKey("briefing_episodes.id", ondelete="CASCADE"), nullable=False
    )
    finding_id: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    user = relationship("ListenerUser", back_populates="feedback")
    episode = relationship("BriefingEpisode", back_populates="feedback")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "episode_id",
            "finding_id",
            name="uq_listener_feedback_user_episode_finding",
        ),
        Index("ix_listener_feedback_user", "user_id"),
        Index("ix_listener_feedback_episode", "episode_id"),
    )

    def __repr__(self) -> str:
        return f"<ListenerFeedback user={self.user_id} episode={self.episode_id} rating={self.rating}>"


class ListenerExternalFeed(TimestampMixin, Base):
    """A user's personal RSS feed subscription."""

    __tablename__ = "listener_external_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("listener_users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("ListenerUser", back_populates="external_feeds")

    def __repr__(self) -> str:
        return f"<ListenerExternalFeed {self.name!r}>"
