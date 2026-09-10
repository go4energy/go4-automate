"""Embedding client — local Ollama (primary) with OpenAI fallback.

The intel module needs 1024-dimensional text embeddings to detect
semantically trivial diffs (whitespace/date-only changes) before
spending Anthropic tokens on triage + reason.

Architecture:
- Primary: local Ollama at ``settings.intel_ollama_url``, model
  ``BAAI/bge-m3`` exposed as ``bge-m3:latest``. Ollama is a shared
  host service (``OLLAMA_HOST=0.0.0.0``, systemd-managed) that other
  projects on the box already use. We just speak its HTTP API; we do
  NOT import any cross-project code or share volumes.
- Optional fallback: OpenAI ``text-embedding-3-small`` with
  ``dimensions=1024`` matching the pgvector column dim. Enabled when
  ``settings.intel_openai_fallback_enabled`` is True and Ollama errors.
- If both fail, callers (fetch_one) catch ``EmbeddingUnavailableError``
  and persist the snapshot with ``embedding=NULL``. The diff pipeline
  then falls back to content_hash + text-similarity, which is enough
  for ~90% of change detection.
"""

from __future__ import annotations

import httpx
from loguru import logger

from app.config import settings


class EmbeddingUnavailableError(Exception):
    """Both Ollama and OpenAI failed (or were not configured)."""


class EmbeddingClient:
    """Async HTTP client for text embeddings via Ollama → OpenAI fallback."""

    def __init__(
        self,
        ollama_url: str | None = None,
        ollama_model: str | None = None,
        openai_api_key: str | None = None,
        openai_model: str | None = None,
        timeout_sec: float = 15.0,
    ) -> None:
        self._ollama_url = (ollama_url or settings.intel_ollama_url).rstrip("/")
        self._ollama_model = ollama_model or settings.intel_ollama_model
        self._openai_key = openai_api_key or settings.openai_api_key
        self._openai_model = openai_model or settings.intel_openai_embed_model
        self._timeout = timeout_sec

    # ── Public API ───────────────────────────────────────────────────

    async def health(self) -> bool:
        """Return True if Ollama responds 200 on /api/version within 2s."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self._ollama_url}/api/version")
                return r.status_code == 200
        except Exception:
            return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        Tries Ollama first; on failure and if configured, falls back
        to OpenAI. Raises ``EmbeddingUnavailableError`` if both fail.
        """
        if not texts:
            return []

        try:
            return await self._embed_ollama(texts)
        except EmbeddingUnavailableError as ollama_err:
            if not settings.intel_openai_fallback_enabled or not self._openai_key:
                raise
            logger.info(
                "Ollama embed failed ({e}); trying OpenAI fallback",
                e=str(ollama_err),
            )
            try:
                return await self._embed_openai(texts)
            except EmbeddingUnavailableError as openai_err:
                raise EmbeddingUnavailableError(
                    f"Ollama: {ollama_err} | OpenAI: {openai_err}"
                ) from openai_err

    async def embed_one(self, text: str) -> list[float]:
        vectors = await self.embed([text])
        return vectors[0] if vectors else []

    # ── Ollama backend ──────────────────────────────────────────────

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        """Hit ``POST /api/embed`` on local Ollama.

        Newer Ollama versions accept a list in ``input`` and return
        ``{"embeddings": [[...], [...]]}``. We use that batch path.
        """
        payload = {"model": self._ollama_model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    f"{self._ollama_url}/api/embed", json=payload
                )
                r.raise_for_status()
                data = r.json()
        except (TimeoutError, httpx.HTTPError) as e:
            raise EmbeddingUnavailableError(f"ollama HTTP: {e}") from e

        vectors = data.get("embeddings")
        if not isinstance(vectors, list) or not all(
            isinstance(v, list) for v in vectors
        ):
            raise EmbeddingUnavailableError(
                f"ollama unexpected response shape: keys={list(data.keys())}"
            )

        expected = settings.intel_embed_dim
        for i, vec in enumerate(vectors):
            if len(vec) != expected:
                raise EmbeddingUnavailableError(
                    f"ollama vector {i} dim {len(vec)} != expected {expected}"
                )
        return vectors

    # ── OpenAI fallback ─────────────────────────────────────────────

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """Hit OpenAI ``/v1/embeddings`` with ``dimensions=1024`` so the
        result fits our pgvector column without reshape.
        """
        payload = {
            "model": self._openai_model,
            "input": texts,
            "dimensions": settings.intel_embed_dim,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._openai_key}"},
                )
                r.raise_for_status()
                data = r.json()
        except (TimeoutError, httpx.HTTPError) as e:
            raise EmbeddingUnavailableError(f"openai HTTP: {e}") from e

        items = data.get("data") or []
        vectors = [item.get("embedding") for item in items]
        if not vectors or not all(isinstance(v, list) for v in vectors):
            raise EmbeddingUnavailableError(
                f"openai unexpected response shape: keys={list(data.keys())}"
            )
        expected = settings.intel_embed_dim
        for i, vec in enumerate(vectors):
            if len(vec) != expected:
                raise EmbeddingUnavailableError(
                    f"openai vector {i} dim {len(vec)} != expected {expected}"
                )
        return vectors


_default_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    """Module-level singleton accessor."""
    global _default_client
    if _default_client is None:
        _default_client = EmbeddingClient()
    return _default_client
