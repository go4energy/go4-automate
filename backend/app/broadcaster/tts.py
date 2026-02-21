"""TTS service - configurable Text-to-Speech via HTTP (Piper or disabled)."""

import httpx
from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError


class TTSService:
    """Configurable TTS: Piper (local/remote) or disabled."""

    def __init__(self) -> None:
        self.engine = settings.tts_engine
        self.piper_url = settings.tts_url

    async def synthesize(self, text: str, voice: str) -> bytes:
        """Convert text to WAV audio bytes via configured TTS engine."""
        if self.engine == "disabled":
            raise ExternalServiceError("TTS", "TTS ist deaktiviert")

        logger.info(
            "TTS synthesize: engine={engine} voice={voice} text_len={length}",
            engine=self.engine,
            voice=voice,
            length=len(text),
        )
        return await self._call_piper(text, voice)

    async def _call_piper(self, text: str, voice: str) -> bytes:
        """HTTP POST to Piper TTS server."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.piper_url}/api/tts",
                    json={"text": text, "voice": voice},
                    timeout=120.0,
                )
                resp.raise_for_status()
                return resp.content
        except httpx.ConnectError as e:
            logger.error("TTS-Server nicht erreichbar: {url}", url=self.piper_url)
            raise ExternalServiceError(
                "TTS", f"Server nicht erreichbar: {self.piper_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error("TTS-Fehler: status={status}", status=e.response.status_code)
            raise ExternalServiceError("TTS", f"HTTP {e.response.status_code}") from e
        except Exception as e:
            logger.exception("TTS-Fehler: {err}", err=str(e))
            raise ExternalServiceError("TTS", str(e)) from e

    def is_available(self) -> bool:
        """Check if TTS is configured and not disabled."""
        return self.engine != "disabled"
