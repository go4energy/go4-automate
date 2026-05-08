"""TTS service - configurable Text-to-Speech via HTTP (Piper, XTTS v2, or disabled)."""

import httpx
from loguru import logger

from app.config import settings
from app.exceptions import ExternalServiceError


class TTSService:
    """Configurable TTS: Piper, XTTS v2, or disabled."""

    def __init__(self, engine_override: str | None = None) -> None:
        self.engine = engine_override or settings.tts_engine
        self.piper_url = settings.tts_url
        self.xtts_url = settings.xtts_url

    async def synthesize(
        self,
        text: str,
        voice: str,
        language: str = "de",
        speaker_wav: str | None = None,
    ) -> bytes:
        """Convert text to WAV audio bytes via configured TTS engine."""
        if self.engine == "disabled":
            raise ExternalServiceError("TTS", "TTS ist deaktiviert")

        logger.info(
            "TTS synthesize: engine={engine} voice={voice} text_len={length}",
            engine=self.engine,
            voice=voice,
            length=len(text),
        )

        if self.engine == "xtts":
            return await self._call_xtts(text, speaker_wav or voice, language)
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

    async def _call_xtts(self, text: str, speaker_wav: str, language: str) -> bytes:
        """HTTP POST to XTTS v2 server."""
        # Resolve speaker name to absolute file path if not already a path
        if speaker_wav and not speaker_wav.startswith("/"):
            from pathlib import Path

            # Try xtts directory first (tenant-prefixed), then raw name
            xtts_dir = Path(settings.speaker_upload_dir).resolve() / "xtts"
            candidates = [
                xtts_dir / f"{speaker_wav}.wav",
                xtts_dir / f"go4energy_{speaker_wav}.wav",
            ]
            for candidate in candidates:
                if candidate.exists():
                    speaker_wav = str(candidate)
                    break
            else:
                # Check all tenant dirs
                for tenant_dir in Path(settings.speaker_upload_dir).resolve().iterdir():
                    if tenant_dir.is_dir() and tenant_dir.name != "xtts":
                        wav = tenant_dir / f"{speaker_wav}.wav"
                        if wav.exists():
                            speaker_wav = str(wav)
                            break

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.xtts_url}/tts_to_audio/",
                    json={
                        "text": text,
                        "speaker_wav": speaker_wav,
                        "language": language,
                    },
                    timeout=300.0,
                )
                resp.raise_for_status()
                return resp.content
        except httpx.ConnectError as e:
            logger.error("XTTS-Server nicht erreichbar: {url}", url=self.xtts_url)
            raise ExternalServiceError(
                "TTS", f"XTTS-Server nicht erreichbar: {self.xtts_url}"
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error("XTTS-Fehler: status={status}", status=e.response.status_code)
            raise ExternalServiceError(
                "TTS", f"XTTS HTTP {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.exception("XTTS-Fehler: {err}", err=str(e))
            raise ExternalServiceError("TTS", str(e)) from e

    def is_available(self) -> bool:
        """Check if TTS is configured and not disabled."""
        return self.engine != "disabled"
