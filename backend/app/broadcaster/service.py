"""Broadcaster service - episode generation pipeline."""

import struct
import wave
from datetime import datetime
from io import BytesIO
from pathlib import Path

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.broadcaster.models import (
    BriefingChannel,
    BriefingEpisode,
    ListenerSubscription,
    ListenerUser,
)
from app.broadcaster.tts import TTSService
from app.config import settings
from app.exceptions import ExternalServiceError, NotFoundError


class BroadcasterService:
    """Orchestrates briefing episode generation: Findings → Script → TTS → Episode."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Channel CRUD ---

    async def list_channels(self, tenant_id: str) -> list[dict]:
        """List all channels with episode and subscriber counts."""
        result = await self.db.execute(
            select(BriefingChannel)
            .where(BriefingChannel.tenant_id == tenant_id)
            .order_by(BriefingChannel.created_at.desc())
        )
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

    async def create_channel(self, tenant_id: str, data: dict) -> BriefingChannel:
        """Create a new briefing channel."""
        channel = BriefingChannel(tenant_id=tenant_id, **data)
        self.db.add(channel)
        await self.db.flush()
        await self.db.refresh(channel)
        logger.info(
            "Channel erstellt: {name} (Tenant: {tenant})",
            name=channel.name,
            tenant=tenant_id,
        )
        return channel

    async def update_channel(
        self, tenant_id: str, channel_id: int, data: dict
    ) -> BriefingChannel:
        """Update an existing channel."""
        channel = await self._get_channel(tenant_id, channel_id)
        for key, value in data.items():
            if value is not None:
                setattr(channel, key, value)
        await self.db.flush()
        await self.db.refresh(channel)
        return channel

    async def delete_channel(self, tenant_id: str, channel_id: int) -> None:
        """Delete a channel and all its episodes."""
        channel = await self._get_channel(tenant_id, channel_id)
        await self.db.delete(channel)
        await self.db.flush()
        logger.info(
            "Channel geloescht: {name} (Tenant: {tenant})",
            name=channel.name,
            tenant=tenant_id,
        )

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
            tts = TTSService()
            audio_url = None
            audio_duration = None
            audio_size = None

            if tts.is_available():
                try:
                    audio_bytes = await tts.synthesize(transcript, channel.voice)
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

    # --- Private helpers ---

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
        """Fetch collector findings matching channel categories."""
        from app.collector.models import CollectorFinding

        query = select(CollectorFinding).where(
            CollectorFinding.tenant_id == tenant_id,
            CollectorFinding.status.in_(["new", "reviewed"]),
        )

        # Filter by channel categories if specified
        if channel.categories:
            query = query.where(
                CollectorFinding.categories.op("&&")(channel.categories)
            )

        query = query.order_by(CollectorFinding.created_at.desc()).limit(
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
        audio_dir = Path(settings.broadcaster_audio_dir) / tenant_id / slug
        audio_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{episode_number}.wav"
        filepath = audio_dir / filename
        filepath.write_bytes(audio_bytes)

        # Calculate duration from WAV header
        duration = self._get_wav_duration(audio_bytes)

        audio_url = f"{settings.broadcaster_audio_dir}/{tenant_id}/{slug}/{filename}"
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
