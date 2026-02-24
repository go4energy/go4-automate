"""Briefing service - episode generation pipeline."""

import struct
import wave
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx
from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.briefing.models import (
    BriefingChannel,
    BriefingChannelSource,
    BriefingEpisode,
    BriefingFinding,
    BriefingSource,
    ListenerSubscription,
    ListenerUser,
)
from app.briefing.tts import TTSService
from app.config import settings
from app.exceptions import ExternalServiceError, ForbiddenError, NotFoundError


class BriefingService:
    """Orchestrates briefing episode generation: Findings → Script → TTS → Episode."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Channel CRUD ---

    async def list_channels(
        self, tenant_id: str, user_id: int | None = None
    ) -> list[dict]:
        """List channels visible to user: org-wide + own personal."""
        query = select(BriefingChannel).where(BriefingChannel.tenant_id == tenant_id)
        if user_id is not None:
            query = query.where(
                or_(
                    BriefingChannel.user_id.is_(None),
                    BriefingChannel.user_id == user_id,
                )
            )
        query = query.order_by(BriefingChannel.created_at.desc())
        result = await self.db.execute(query)
        channels = result.scalars().all()

        items = []
        for ch in channels:
            ep_count = await self._count_episodes(ch.id)
            sub_count = await self._count_subscribers(ch.id)
            item = ch.__dict__.copy()
            item["episode_count"] = ep_count
            item["subscriber_count"] = sub_count
            items.append(item)
        return items

    async def get_channel(self, tenant_id: str, channel_id: int) -> dict:
        """Get a single channel with counts."""
        channel = await self._get_channel(tenant_id, channel_id)
        result = channel.__dict__.copy()
        result["episode_count"] = await self._count_episodes(channel.id)
        result["subscriber_count"] = await self._count_subscribers(channel.id)
        return result

    async def create_channel(
        self, tenant_id: str, data: dict, user_id: int | None = None
    ) -> BriefingChannel:
        """Create a new briefing channel. user_id=None means org-wide."""
        channel = BriefingChannel(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(channel)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(
            "Channel erstellt: {name} (Tenant: {tenant}, User: {uid})",
            name=channel.name,
            tenant=tenant_id,
            uid=user_id,
        )
        return channel

    async def update_channel(
        self,
        tenant_id: str,
        channel_id: int,
        data: dict,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> BriefingChannel:
        """Update a channel. Ownership check: own or admin for org."""
        channel = await self._get_channel(tenant_id, channel_id)
        self._check_ownership(channel.user_id, user_id, is_admin)
        for key, value in data.items():
            if value is not None:
                setattr(channel, key, value)
        await self.db.flush()
        await self.db.refresh(channel)
        return channel

    async def delete_channel(
        self,
        tenant_id: str,
        channel_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        """Delete a channel. Ownership check: own or admin for org."""
        channel = await self._get_channel(tenant_id, channel_id)
        self._check_ownership(channel.user_id, user_id, is_admin)
        await self.db.delete(channel)
        await self.db.flush()
        logger.info(
            "Channel geloescht: {name} (Tenant: {tenant})",
            name=channel.name,
            tenant=tenant_id,
        )

    async def clone_channel(
        self,
        tenant_id: str,
        channel_id: int,
        user_id: int,
        overrides: dict | None = None,
    ) -> BriefingChannel:
        """Clone an org channel as a personal channel for user."""
        original = await self._get_channel(tenant_id, channel_id)
        if original.user_id is not None:
            raise ForbiddenError("Nur Org-Channels koennen geklont werden")

        overrides = overrides or {}
        name = overrides.get("name") or f"{original.name} (Mein)"
        slug = overrides.get("slug") or f"{original.slug}-{user_id}"

        clone = BriefingChannel(
            tenant_id=tenant_id,
            user_id=user_id,
            cloned_from_id=original.id,
            name=name,
            slug=slug,
            description=original.description,
            target_audience=original.target_audience,
            tags=original.tags or [],
            streams=original.streams or [],
            schedule=original.schedule,
            voice=original.voice,
            language=original.language,
            intro_text=original.intro_text,
            outro_text=original.outro_text,
            personal_context_enabled=original.personal_context_enabled,
            max_items=original.max_items,
            max_duration_minutes=original.max_duration_minutes,
            cover_image_url=original.cover_image_url,
            output_format=original.output_format,
            text_format=original.text_format,
        )
        self.db.add(clone)
        await self.db.flush()

        # Copy source links
        result = await self.db.execute(
            select(BriefingChannelSource).where(
                BriefingChannelSource.channel_id == original.id
            )
        )
        for link in result.scalars().all():
            new_link = BriefingChannelSource(
                channel_id=clone.id, source_id=link.source_id
            )
            self.db.add(new_link)
        await self.db.flush()
        await self.db.refresh(clone)

        logger.info(
            "Channel geklont: {orig} -> {clone} (User: {uid})",
            orig=original.name,
            clone=clone.name,
            uid=user_id,
        )
        return clone

    # --- Source CRUD ---

    @staticmethod
    def _sanitize_source(source: BriefingSource) -> dict:
        """Build a response dict from source, stripping oauth_token and adding computed fields."""
        data = source.__dict__.copy()
        cfg = data.get("config") or {}
        data["oauth_connected"] = bool(cfg.get("oauth_token"))
        data["oauth_email"] = cfg.get("oauth_email")
        # Strip encrypted token from response
        if "oauth_token" in cfg:
            safe_cfg = {k: v for k, v in cfg.items() if k != "oauth_token"}
            data["config"] = safe_cfg
        return data

    async def list_sources(
        self,
        tenant_id: str,
        source_type: str | None = None,
        active: bool | None = None,
        user_id: int | None = None,
    ) -> list[dict]:
        """List sources visible to user: org-wide + own personal."""
        query = select(BriefingSource).where(BriefingSource.tenant_id == tenant_id)
        if user_id is not None:
            query = query.where(
                or_(
                    BriefingSource.user_id.is_(None),
                    BriefingSource.user_id == user_id,
                )
            )
        if source_type:
            query = query.where(BriefingSource.source_type == source_type)
        if active is not None:
            query = query.where(BriefingSource.active == active)
        query = query.order_by(BriefingSource.created_at.desc())
        result = await self.db.execute(query)
        return [self._sanitize_source(s) for s in result.scalars().all()]

    async def get_source(
        self, tenant_id: str, source_id: int, *, raw: bool = False
    ) -> BriefingSource | dict:
        """Get a single source or raise NotFoundError. raw=True returns ORM object."""
        result = await self.db.execute(
            select(BriefingSource).where(
                BriefingSource.id == source_id,
                BriefingSource.tenant_id == tenant_id,
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise NotFoundError("BriefingSource", source_id)
        if raw:
            return source
        return self._sanitize_source(source)

    async def create_source(
        self, tenant_id: str, data: dict, user_id: int | None = None
    ) -> dict:
        """Create a new briefing source. user_id=None means org-wide."""
        source = BriefingSource(tenant_id=tenant_id, user_id=user_id, **data)
        self.db.add(source)
        await self.db.flush()
        await self.db.refresh(source)
        logger.info(
            "Briefing-Source erstellt: {name} ({stype}, Tenant: {tenant}, User: {uid})",
            name=source.name,
            stype=source.source_type,
            tenant=tenant_id,
            uid=user_id,
        )
        return self._sanitize_source(source)

    async def update_source(
        self,
        tenant_id: str,
        source_id: int,
        data: dict,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> dict:
        """Update a briefing source. Ownership check: own or admin for org."""
        source = await self.get_source(tenant_id, source_id, raw=True)
        self._check_ownership(source.user_id, user_id, is_admin)
        for key, value in data.items():
            if value is not None:
                setattr(source, key, value)
        await self.db.flush()
        await self.db.refresh(source)
        return self._sanitize_source(source)

    async def delete_source(
        self,
        tenant_id: str,
        source_id: int,
        user_id: int | None = None,
        is_admin: bool = False,
    ) -> None:
        """Delete a briefing source. Ownership check: own or admin for org."""
        source = await self.get_source(tenant_id, source_id, raw=True)
        self._check_ownership(source.user_id, user_id, is_admin)
        await self.db.delete(source)
        await self.db.flush()
        logger.info(
            "Briefing-Source geloescht: {name} (Tenant: {tenant})",
            name=source.name,
            tenant=tenant_id,
        )

    async def disconnect_oauth(self, tenant_id: str, source_id: int) -> dict:
        """Remove OAuth tokens from a source config."""
        source = await self.get_source(tenant_id, source_id, raw=True)
        cfg = dict(source.config or {})
        for key in (
            "oauth_token",
            "oauth_email",
            "oauth_provider",
            "oauth_connected_at",
        ):
            cfg.pop(key, None)
        # Assign new dict to ensure SQLAlchemy detects JSONB mutation
        source.config = cfg
        await self.db.flush()
        await self.db.refresh(source)
        return self._sanitize_source(source)

    # --- Finding CRUD ---

    async def list_findings(
        self,
        tenant_id: str,
        status: str | None = None,
        source_id: int | None = None,
        source_type: str | None = None,
        user_id: int | None = None,
    ) -> list[BriefingFinding]:
        """List findings visible to user via source ownership."""
        query = select(BriefingFinding).where(BriefingFinding.tenant_id == tenant_id)
        if user_id is not None:
            visible_sources = select(BriefingSource.id).where(
                BriefingSource.tenant_id == tenant_id,
                or_(
                    BriefingSource.user_id.is_(None),
                    BriefingSource.user_id == user_id,
                ),
            )
            query = query.where(
                or_(
                    BriefingFinding.source_id.in_(visible_sources),
                    BriefingFinding.source_id.is_(None),
                )
            )
        if status:
            query = query.where(BriefingFinding.status == status)
        if source_id:
            query = query.where(BriefingFinding.source_id == source_id)
        if source_type:
            query = query.where(BriefingFinding.source_type == source_type)
        query = query.order_by(BriefingFinding.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_finding(
        self, tenant_id: str, finding_id: int, data: dict
    ) -> BriefingFinding:
        """Update a briefing finding (e.g., status change)."""
        result = await self.db.execute(
            select(BriefingFinding).where(
                BriefingFinding.id == finding_id,
                BriefingFinding.tenant_id == tenant_id,
            )
        )
        finding = result.scalar_one_or_none()
        if not finding:
            raise NotFoundError("BriefingFinding", finding_id)
        for key, value in data.items():
            if value is not None:
                setattr(finding, key, value)
        await self.db.flush()
        await self.db.refresh(finding)
        return finding

    async def bulk_delete_findings(self, tenant_id: str, finding_ids: list[int]) -> int:
        """Bulk delete findings by IDs."""
        from sqlalchemy import delete

        stmt = delete(BriefingFinding).where(
            BriefingFinding.tenant_id == tenant_id,
            BriefingFinding.id.in_(finding_ids),
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    # --- Source Runner ---

    async def run_sources(self, tenant_id: str, source_id: int | None = None) -> dict:
        """Run source fetching for due sources (or a specific source)."""
        if source_id:
            source = await self.get_source(tenant_id, source_id, raw=True)
            sources = [source]
        else:
            sources = await self._get_due_sources(tenant_id)

        total_new = 0
        errors: list[str] = []

        for source in sources:
            try:
                raw_items = await self._fetch_source(source)
                new_findings = await self._deduplicate_and_save(
                    tenant_id, source, raw_items
                )
                total_new += len(new_findings)
                source.last_fetched_at = datetime.utcnow()
                await self.db.flush()
            except Exception as e:
                msg = f"{source.name}: {e}"
                errors.append(msg)
                logger.warning("Source-Fetch fehlgeschlagen: {msg}", msg=msg)

        return {
            "sources_processed": len(sources),
            "findings_new": total_new,
            "errors": errors,
        }

    async def _get_due_sources(self, tenant_id: str) -> list[BriefingSource]:
        """Get active sources that are due for fetching."""
        result = await self.db.execute(
            select(BriefingSource).where(
                BriefingSource.tenant_id == tenant_id,
                BriefingSource.active.is_(True),
            )
        )
        sources = list(result.scalars().all())

        now = datetime.utcnow()
        due = []
        for s in sources:
            if not s.last_fetched_at:
                due.append(s)
            else:
                from datetime import timedelta

                if now - s.last_fetched_at >= timedelta(hours=s.fetch_interval_hours):
                    due.append(s)
        return due

    async def _fetch_source(self, source: BriefingSource) -> list[dict]:
        """Dispatch fetching to the appropriate handler based on source_type."""
        from app.utils.source_fetchers import (
            fetch_rss,
            fetch_websearch,
            fetch_website,
        )

        if source.source_type == "rss":
            return await fetch_rss(source.url, source.keywords)
        elif source.source_type == "website":
            cfg = source.config or {}
            selector = cfg.get("selector", "article, .post, .entry")
            return await fetch_website(source.url, source.keywords, selector)
        elif source.source_type == "websearch":
            return await fetch_websearch(source.keywords, settings.serper_api_key)
        elif source.source_type in ("calendar", "email"):
            return await self._fetch_oauth_source(source)
        elif source.source_type == "kpi":
            logger.info("Source-Typ kpi noch nicht implementiert")
            return []
        else:
            logger.warning("Unbekannter Source-Typ: {stype}", stype=source.source_type)
            return []

    async def _fetch_oauth_source(self, source: BriefingSource) -> list[dict]:
        """Fetch from an OAuth-connected source (calendar/email)."""
        from app.briefing.oauth import (
            decrypt_token,
            encrypt_token,
            refresh_google_token,
            refresh_microsoft_token,
        )
        from app.utils.source_fetchers import fetch_calendar, fetch_emails

        cfg = source.config or {}
        encrypted = cfg.get("oauth_token")
        provider = cfg.get("oauth_provider", "microsoft")
        if not encrypted:
            logger.warning("Source {sid} hat keine OAuth-Verbindung", sid=source.id)
            return []

        token_data = decrypt_token(encrypted)
        access_token = token_data["access_token"]

        # Refresh if expired (5 min buffer)
        expires_at = token_data.get("expires_at", 0)
        if datetime.utcnow().timestamp() >= expires_at - 300:
            if provider == "microsoft":
                refreshed = await refresh_microsoft_token(token_data["refresh_token"])
            else:
                refreshed = await refresh_google_token(token_data["refresh_token"])
            access_token = refreshed["access_token"]
            token_data["access_token"] = access_token
            token_data["refresh_token"] = refreshed.get(
                "refresh_token", token_data["refresh_token"]
            )
            token_data["expires_at"] = datetime.utcnow().timestamp() + refreshed.get(
                "expires_in", 3600
            )
            cfg["oauth_token"] = encrypt_token(token_data)
            source.config = cfg
            await self.db.flush()

        days = cfg.get("days_back", 7)
        try:
            if source.source_type == "calendar":
                return await fetch_calendar(access_token, provider, days)
            else:
                return await fetch_emails(access_token, provider, days, source.keywords)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("OAuth Token ungueltig fuer Source {sid}", sid=source.id)
                return []
            raise ExternalServiceError(f"OAuth ({provider})", str(e)) from e

    async def _deduplicate_and_save(
        self,
        tenant_id: str,
        source: BriefingSource,
        raw_items: list[dict],
    ) -> list[BriefingFinding]:
        """Save findings, skip duplicates by URL. Inherit tags/streams from source."""
        new_findings: list[BriefingFinding] = []

        for item in raw_items:
            url = item.get("url", "")
            if not url:
                continue

            existing = await self.db.execute(
                select(BriefingFinding).where(
                    BriefingFinding.tenant_id == tenant_id,
                    BriefingFinding.url == url,
                )
            )
            if existing.scalar_one_or_none():
                continue

            finding = BriefingFinding(
                tenant_id=tenant_id,
                source_id=source.id,
                title=item.get("title", "")[:500],
                summary=item.get("summary"),
                url=url,
                content_snippet=item.get("content_snippet"),
                found_at=item.get("found_at", datetime.utcnow()),
                source_type=source.source_type,
                tags=source.tags or [],
                streams=source.streams or [],
            )
            self.db.add(finding)
            new_findings.append(finding)

        if new_findings:
            await self.db.flush()

        return new_findings

    # --- Channel-Source Linking ---

    async def link_source_to_channel(
        self, tenant_id: str, channel_id: int, source_id: int
    ) -> BriefingChannelSource:
        """Link a source to a channel."""
        await self._get_channel(tenant_id, channel_id)
        await self.get_source(tenant_id, source_id)

        link = BriefingChannelSource(channel_id=channel_id, source_id=source_id)
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def unlink_source_from_channel(
        self, tenant_id: str, channel_id: int, source_id: int
    ) -> None:
        """Unlink a source from a channel."""
        result = await self.db.execute(
            select(BriefingChannelSource).where(
                BriefingChannelSource.channel_id == channel_id,
                BriefingChannelSource.source_id == source_id,
            )
        )
        link = result.scalar_one_or_none()
        if not link:
            raise NotFoundError("BriefingChannelSource", f"{channel_id}/{source_id}")
        await self.db.delete(link)
        await self.db.flush()

    async def list_channel_sources(self, tenant_id: str, channel_id: int) -> list[dict]:
        """List sources linked to a channel."""
        await self._get_channel(tenant_id, channel_id)
        result = await self.db.execute(
            select(BriefingSource)
            .join(
                BriefingChannelSource,
                BriefingChannelSource.source_id == BriefingSource.id,
            )
            .where(BriefingChannelSource.channel_id == channel_id)
        )
        return [self._sanitize_source(s) for s in result.scalars().all()]

    # --- Episode CRUD ---

    async def list_episodes(self, channel_id: int) -> list[BriefingEpisode]:
        """List episodes for a channel."""
        result = await self.db.execute(
            select(BriefingEpisode)
            .where(BriefingEpisode.channel_id == channel_id)
            .order_by(BriefingEpisode.episode_number.desc())
        )
        return list(result.scalars().all())

    async def get_episode(self, episode_id: int) -> BriefingEpisode:
        """Get a single episode."""
        result = await self.db.execute(
            select(BriefingEpisode).where(BriefingEpisode.id == episode_id)
        )
        episode = result.scalar_one_or_none()
        if not episode:
            raise NotFoundError("Episode", episode_id)
        return episode

    async def delete_episode(self, episode_id: int) -> None:
        """Delete an episode."""
        episode = await self.get_episode(episode_id)
        await self.db.delete(episode)
        await self.db.flush()

    # --- Episode Generation Pipeline ---

    async def generate_episode(
        self, tenant_id: str, channel_id: int, tenant_config: dict
    ) -> BriefingEpisode:
        """Full pipeline: Findings → LLM Script → TTS Audio → Episode."""
        channel = await self._get_channel(tenant_id, channel_id)

        # Determine episode number
        next_num = await self._next_episode_number(channel_id)

        # Create episode in generating state
        now = datetime.utcnow()
        title = f"{channel.name} — {now.strftime('%d. %b %Y')}"
        episode = BriefingEpisode(
            tenant_id=tenant_id,
            channel_id=channel_id,
            episode_number=next_num,
            title=title,
            status="generating",
        )
        self.db.add(episode)
        await self.db.flush()
        await self.db.refresh(episode)

        try:
            # 1. Fetch findings matching channel categories
            findings = await self._fetch_findings(tenant_id, channel)

            # 2. Generate script via LLM
            transcript = await self._generate_script(channel, findings, tenant_config)

            # 3. TTS: Script → Audio
            channel_engine = channel.tts_engine or settings.tts_engine
            tts = TTSService(engine_override=channel_engine)
            audio_url = None
            audio_duration = None
            audio_size = None

            if tts.is_available():
                try:
                    if channel_engine == "xtts" and channel.xtts_speaker_id:
                        speaker = await self._get_speaker(channel.xtts_speaker_id)
                        audio_bytes = await tts.synthesize(
                            transcript,
                            speaker.xtts_speaker_name,
                            language=channel.language,
                        )
                    else:
                        audio_bytes = await tts.synthesize(
                            transcript, channel.voice, language=channel.language
                        )
                    audio_url, audio_duration, audio_size = await self._save_audio(
                        tenant_id, channel.slug, next_num, audio_bytes
                    )
                except ExternalServiceError as e:
                    logger.warning(
                        "TTS fehlgeschlagen, Episode ohne Audio: {err}", err=e.message
                    )

            # 4. Update episode
            episode.transcript = transcript
            episode.summary = transcript[:500] if transcript else None
            episode.audio_url = audio_url
            episode.audio_duration_seconds = audio_duration
            episode.audio_size_bytes = audio_size
            episode.findings_used = [{"id": f.id, "title": f.title} for f in findings]
            episode.status = "ready"
            episode.generated_at = datetime.utcnow()
            episode.published_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(episode)

            logger.info(
                "Episode generiert: #{num} fuer {channel} ({findings} Findings)",
                num=next_num,
                channel=channel.name,
                findings=len(findings),
            )
            return episode

        except Exception as e:
            episode.status = "failed"
            episode.error_message = str(e)
            await self.db.flush()
            logger.exception("Episode-Generierung fehlgeschlagen: {err}", err=str(e))
            raise

    # --- Listener User Management (Admin) ---

    async def list_users(self, tenant_id: str) -> list[dict]:
        """List all listener users for admin view."""
        result = await self.db.execute(
            select(ListenerUser)
            .where(ListenerUser.tenant_id == tenant_id)
            .order_by(ListenerUser.created_at.desc())
        )
        users = result.scalars().all()

        items = []
        for user in users:
            sub_count = await self.db.execute(
                select(func.count(ListenerSubscription.id)).where(
                    ListenerSubscription.user_id == user.id
                )
            )
            item = user.__dict__.copy()
            item["subscription_count"] = sub_count.scalar() or 0
            items.append(item)
        return items

    async def create_user(self, tenant_id: str, data: dict) -> ListenerUser:
        """Create a listener user (admin)."""
        from passlib.hash import bcrypt

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
        logger.info(
            "Listener-User erstellt: {email} (Tenant: {tenant})",
            email=user.email,
            tenant=tenant_id,
        )
        return user

    async def delete_user(self, tenant_id: str, user_id: int) -> None:
        """Delete a listener user."""
        result = await self.db.execute(
            select(ListenerUser).where(
                ListenerUser.id == user_id,
                ListenerUser.tenant_id == tenant_id,
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("ListenerUser", user_id)
        await self.db.delete(user)
        await self.db.flush()

    # --- Speaker CRUD ---

    async def list_speakers(self, tenant_id: str) -> list:
        """List all speakers for a tenant."""
        from app.briefing.models import BriefingSpeaker

        result = await self.db.execute(
            select(BriefingSpeaker)
            .where(BriefingSpeaker.tenant_id == tenant_id)
            .order_by(BriefingSpeaker.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_speaker(self, tenant_id: str, speaker_id: int) -> object:
        """Get a single speaker or raise NotFoundError."""
        from app.briefing.models import BriefingSpeaker

        result = await self.db.execute(
            select(BriefingSpeaker).where(
                BriefingSpeaker.id == speaker_id,
                BriefingSpeaker.tenant_id == tenant_id,
            )
        )
        speaker = result.scalar_one_or_none()
        if not speaker:
            raise NotFoundError("Speaker", speaker_id)
        return speaker

    async def create_speaker(
        self,
        tenant_id: str,
        name: str,
        language: str,
        file_bytes: bytes,
        description: str | None = None,
    ) -> object:
        """Create a speaker from uploaded WAV file."""
        from app.briefing.models import BriefingSpeaker

        # Validate WAV format
        duration, sample_rate = self._validate_wav(file_bytes)

        # Generate safe filename
        safe_name = self._safe_filename(name)

        # Save canonical copy
        tenant_dir = Path(settings.speaker_upload_dir) / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        canonical_path = tenant_dir / f"{safe_name}.wav"
        canonical_path.write_bytes(file_bytes)

        # Save copy for XTTS container
        xtts_dir = Path(settings.speaker_upload_dir) / "xtts"
        xtts_dir.mkdir(parents=True, exist_ok=True)
        xtts_filename = f"{tenant_id}_{safe_name}.wav"
        xtts_path = xtts_dir / xtts_filename
        xtts_path.write_bytes(file_bytes)

        xtts_speaker_name = f"{tenant_id}_{safe_name}"

        speaker = BriefingSpeaker(
            tenant_id=tenant_id,
            name=name,
            description=description,
            language=language,
            file_path=str(canonical_path),
            file_size_bytes=len(file_bytes),
            duration_seconds=duration,
            sample_rate=sample_rate,
            xtts_speaker_name=xtts_speaker_name,
        )
        self.db.add(speaker)
        await self.db.flush()
        await self.db.refresh(speaker)

        logger.info(
            "Speaker erstellt: {name} ({lang}, {dur}s, Tenant: {tenant})",
            name=name,
            lang=language,
            dur=duration,
            tenant=tenant_id,
        )
        return speaker

    async def delete_speaker(self, tenant_id: str, speaker_id: int) -> None:
        """Delete a speaker and its files."""
        speaker = await self.get_speaker(tenant_id, speaker_id)

        # Delete canonical file
        canonical = Path(speaker.file_path)
        if canonical.exists():
            canonical.unlink()

        # Delete XTTS copy
        if speaker.xtts_speaker_name:
            xtts_path = (
                Path(settings.speaker_upload_dir)
                / "xtts"
                / f"{speaker.xtts_speaker_name}.wav"
            )
            if xtts_path.exists():
                xtts_path.unlink()

        await self.db.delete(speaker)
        await self.db.flush()
        logger.info(
            "Speaker geloescht: {name} (Tenant: {tenant})",
            name=speaker.name,
            tenant=tenant_id,
        )

    def _validate_wav(self, file_bytes: bytes) -> tuple[int, int]:
        """Validate WAV file: must be 6-30s. Returns (duration_seconds, sample_rate)."""
        try:
            bio = BytesIO(file_bytes)
            with wave.open(bio, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate <= 0:
                    raise ValueError("Ungueltige Sample-Rate")
                duration = frames // rate
        except (wave.Error, struct.error, EOFError) as e:
            raise ValueError("Ungueltige WAV-Datei") from e

        if duration < 6:
            raise ValueError(f"Audio zu kurz ({duration}s). Minimum: 6 Sekunden.")
        if duration > 30:
            raise ValueError(f"Audio zu lang ({duration}s). Maximum: 30 Sekunden.")
        return duration, rate

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert a name to a safe filename."""
        import re

        safe = name.lower().strip()
        safe = re.sub(r"[^a-z0-9]+", "-", safe)
        safe = safe.strip("-")
        return safe or "speaker"

    # --- Private helpers ---

    async def _get_speaker(self, speaker_id: int) -> object:
        """Get speaker by ID (no tenant check, internal use)."""
        from app.briefing.models import BriefingSpeaker

        result = await self.db.execute(
            select(BriefingSpeaker).where(BriefingSpeaker.id == speaker_id)
        )
        speaker = result.scalar_one_or_none()
        if not speaker:
            raise NotFoundError("Speaker", speaker_id)
        return speaker

    def _check_ownership(
        self,
        resource_user_id: int | None,
        current_user_id: int | None,
        is_admin: bool,
    ) -> None:
        """Check if user can modify a resource. Admins can modify org resources."""
        if resource_user_id is None and not is_admin:
            raise ForbiddenError("Nur Admins koennen Org-Ressourcen aendern")
        elif (
            resource_user_id is not None
            and resource_user_id != current_user_id
            and not is_admin
        ):
            raise ForbiddenError("Keine Berechtigung fuer diese Ressource")

    async def _get_channel(self, tenant_id: str, channel_id: int) -> BriefingChannel:
        """Get channel or raise NotFoundError."""
        result = await self.db.execute(
            select(BriefingChannel).where(
                BriefingChannel.id == channel_id,
                BriefingChannel.tenant_id == tenant_id,
            )
        )
        channel = result.scalar_one_or_none()
        if not channel:
            raise NotFoundError("Channel", channel_id)
        return channel

    async def _count_episodes(self, channel_id: int) -> int:
        """Count episodes for a channel."""
        result = await self.db.execute(
            select(func.count(BriefingEpisode.id)).where(
                BriefingEpisode.channel_id == channel_id
            )
        )
        return result.scalar() or 0

    async def _count_subscribers(self, channel_id: int) -> int:
        """Count subscribers for a channel."""
        result = await self.db.execute(
            select(func.count(ListenerSubscription.id)).where(
                ListenerSubscription.channel_id == channel_id
            )
        )
        return result.scalar() or 0

    async def _next_episode_number(self, channel_id: int) -> int:
        """Get next episode number for a channel."""
        result = await self.db.execute(
            select(func.max(BriefingEpisode.episode_number)).where(
                BriefingEpisode.channel_id == channel_id
            )
        )
        max_num = result.scalar()
        return (max_num or 0) + 1

    async def _fetch_findings(self, tenant_id: str, channel: BriefingChannel) -> list:
        """Fetch briefing findings matching channel's linked sources, tags, and/or streams."""
        query = select(BriefingFinding).where(
            BriefingFinding.tenant_id == tenant_id,
            BriefingFinding.status.in_(["new", "used"]),
        )

        # Filter by channel's linked sources if any
        linked_source_ids = await self.db.execute(
            select(BriefingChannelSource.source_id).where(
                BriefingChannelSource.channel_id == channel.id
            )
        )
        source_ids = [r[0] for r in linked_source_ids.all()]
        if source_ids:
            query = query.where(BriefingFinding.source_id.in_(source_ids))

        # Filter by channel tags if specified (JSONB ?| text[])
        if channel.tags:
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
            from sqlalchemy.types import String

            query = query.where(
                BriefingFinding.tags.op("?|")(cast(channel.tags, PG_ARRAY(String)))
            )

        # Filter by channel streams if specified (JSONB ?| text[])
        if channel.streams:
            from sqlalchemy import cast
            from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
            from sqlalchemy.types import String

            query = query.where(
                BriefingFinding.streams.op("?|")(
                    cast(channel.streams, PG_ARRAY(String))
                )
            )

        query = query.order_by(BriefingFinding.created_at.desc()).limit(
            channel.max_items
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _generate_script(
        self,
        channel: BriefingChannel,
        findings: list,
        tenant_config: dict,
    ) -> str:
        """Generate a spoken briefing script via LLM."""
        from app.services.llm import LLMService

        llm = LLMService(tenant_config)

        # Build prompt
        company = tenant_config.get("COMPANY_NAME", "")
        findings_text = "\n".join(
            f"- {f.title}: {f.summary or f.content_snippet or ''}" for f in findings
        )

        if not findings_text:
            findings_text = "Keine aktuellen Findings verfuegbar."

        system_prompt = (
            f"Du bist ein professioneller Nachrichtensprecher fuer {company}. "
            f"Zielgruppe: {channel.target_audience or 'Allgemein'}. "
            f"Sprache: {channel.language}. "
            "Erstelle ein Audio-Briefing-Script zum Vorlesen. "
            "Schreibe reinen Sprechtext — kein Markdown, keine Aufzaehlungen, "
            "keine Sonderzeichen. Natuerliche, gesprochene Sprache. "
            f"Max. {channel.max_duration_minutes} Minuten Sprechzeit."
        )

        intro = channel.intro_text or f"Willkommen zum {channel.name}."
        outro = channel.outro_text or "Das war Ihr Briefing fuer heute. Bis morgen!"

        user_prompt = (
            f"Erstelle das Briefing-Script.\n\n"
            f"Intro: {intro}\n\n"
            f"Aktuelle Themen:\n{findings_text}\n\n"
            f"Outro: {outro}\n\n"
            "Fasse die wichtigsten Themen zusammen und verbinde sie fliessend. "
            "Schreibe einen zusammenhaengenden Sprechtext."
        )

        provider = settings.llm_model_briefing
        if provider == "ollama":
            return await self._call_ollama(system_prompt, user_prompt)

        return await llm.generate_with_config(
            provider="anthropic",
            model=settings.llm_model_content,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.6,
            max_tokens=4096,
        )

    async def _call_ollama(self, system: str, prompt: str) -> str:
        """Call Ollama via OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url=f"{settings.ollama_url}/v1", api_key="ollama")
        response = await client.chat.completions.create(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content

    async def _save_audio(
        self, tenant_id: str, slug: str, episode_number: int, audio_bytes: bytes
    ) -> tuple[str, int | None, int]:
        """Save audio file and return (url, duration_seconds, size_bytes)."""
        audio_dir = Path(settings.briefing_audio_dir) / tenant_id / slug
        audio_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{episode_number}.wav"
        filepath = audio_dir / filename
        filepath.write_bytes(audio_bytes)

        # Calculate duration from WAV header
        duration = self._get_wav_duration(audio_bytes)

        audio_url = f"{settings.briefing_audio_dir}/{tenant_id}/{slug}/{filename}"
        return audio_url, duration, len(audio_bytes)

    def _get_wav_duration(self, audio_bytes: bytes) -> int | None:
        """Extract duration in seconds from WAV file bytes."""
        try:
            bio = BytesIO(audio_bytes)
            with wave.open(bio, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames // rate
        except (wave.Error, struct.error, EOFError):
            pass
        return None
