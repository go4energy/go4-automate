"""STT service - Speech-to-Text via faster-whisper or OpenAI."""

from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError


class STTService:
    """Transcribe audio via faster-whisper (local) or OpenAI (cloud)."""

    def __init__(self, provider: str = "faster-whisper") -> None:
        self.provider = provider

    async def transcribe(self, audio_bytes: bytes, language: str = "de") -> str:
        """Convert audio bytes to text."""
        logger.info(
            "STT transcribe: provider={provider} audio_size={size} lang={lang}",
            provider=self.provider,
            size=len(audio_bytes),
            lang=language,
        )

        try:
            if self.provider == "openai":
                return await self._transcribe_openai(audio_bytes, language)
            return await self._transcribe_faster_whisper(audio_bytes, language)
        except ExternalServiceError:
            raise
        except Exception as e:
            logger.exception("STT-Fehler: {err}", err=str(e))
            raise ExternalServiceError("STT", str(e)) from e

    async def _transcribe_faster_whisper(
        self, audio_bytes: bytes, language: str
    ) -> str:
        """Transcribe via faster-whisper OpenAI-compatible API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=settings.stt_url,
            api_key="whisper",
        )
        try:
            response = await client.audio.transcriptions.create(
                model="Systran/faster-whisper-large-v3",
                file=("audio.webm", audio_bytes, "audio/webm"),
                language=language,
            )
            text = response.text.strip()
            logger.info("STT result: {text}", text=text[:100])
            return text
        except Exception as e:
            raise ExternalServiceError("STT", f"faster-whisper Fehler: {e}") from e

    async def _transcribe_openai(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe via OpenAI Whisper API."""
        if not settings.openai_api_key:
            raise ExternalServiceError("STT", "OpenAI API Key nicht konfiguriert")

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.webm", audio_bytes, "audio/webm"),
                language=language,
            )
            text = response.text.strip()
            logger.info("STT result: {text}", text=text[:100])
            return text
        except Exception as e:
            raise ExternalServiceError("STT", f"OpenAI Whisper Fehler: {e}") from e
