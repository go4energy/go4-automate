"""EmbeddingClient integration test against mock Ollama + OpenAI.

Verifies the Ollama-primary, OpenAI-fallback HTTP contract without
hitting real services. The mocks emulate the same response shapes
that the production endpoints return so the parser logic is
exercised end-to-end.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from json import dumps as json_dumps, loads as json_loads

import pytest

from app.config import settings
from app.intel.services.embedding_client import (
    EmbeddingClient,
    EmbeddingUnavailableError,
)


def _start_mock(port: int, ollama_ok: bool = True, openai_ok: bool = True) -> HTTPServer:
    """Stub server that emulates both Ollama and OpenAI endpoints.

    Uses path prefixes:
    - /api/version, /api/embed → Ollama style
    - /v1/embeddings           → OpenAI style
    """
    expected_dim = settings.intel_embed_dim

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *_a, **_kw):  # silence
            return

        def do_GET(self):
            if self.path == "/api/version" and ollama_ok:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"version":"mock"}')
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json_loads(self.rfile.read(length)) if length else {}

            if self.path == "/api/embed":
                if not ollama_ok:
                    self.send_response(503)
                    self.end_headers()
                    return
                inputs = body.get("input") or []
                if isinstance(inputs, str):
                    inputs = [inputs]
                vecs = [[(i + 1) / expected_dim] * expected_dim for i in range(len(inputs))]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json_dumps({"embeddings": vecs}).encode())
                return

            if self.path == "/v1/embeddings":
                if not openai_ok:
                    self.send_response(401)
                    self.end_headers()
                    return
                inputs = body.get("input") or []
                if isinstance(inputs, str):
                    inputs = [inputs]
                data = [
                    {"embedding": [0.1 * (i + 1)] * expected_dim, "index": i}
                    for i in range(len(inputs))
                ]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json_dumps({"data": data}).encode())
                return

            self.send_response(404)
            self.end_headers()

    server = HTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def mock_both_ok():
    port = 19790
    server = _start_mock(port, ollama_ok=True, openai_ok=True)
    try:
        yield port
    finally:
        server.shutdown()


@pytest.fixture(scope="module")
def mock_ollama_down():
    port = 19791
    server = _start_mock(port, ollama_ok=False, openai_ok=True)
    try:
        yield port
    finally:
        server.shutdown()


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_health_ollama_up(mock_both_ok):
    client = EmbeddingClient(ollama_url=f"http://127.0.0.1:{mock_both_ok}")
    assert await client.health() is True


@pytest.mark.anyio
async def test_health_ollama_down(mock_ollama_down):
    client = EmbeddingClient(ollama_url=f"http://127.0.0.1:{mock_ollama_down}")
    assert await client.health() is False


@pytest.mark.anyio
async def test_embed_single_via_ollama(mock_both_ok):
    client = EmbeddingClient(ollama_url=f"http://127.0.0.1:{mock_both_ok}")
    vec = await client.embed_one("hello")
    assert len(vec) == settings.intel_embed_dim


@pytest.mark.anyio
async def test_embed_batch_via_ollama(mock_both_ok):
    client = EmbeddingClient(ollama_url=f"http://127.0.0.1:{mock_both_ok}")
    vectors = await client.embed(["a", "b", "c"])
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == settings.intel_embed_dim


@pytest.mark.anyio
async def test_openai_fallback_triggers_when_ollama_down(mock_ollama_down):
    """When Ollama returns 503 AND OpenAI fallback is enabled, OpenAI is used."""
    original_fb = settings.intel_openai_fallback_enabled
    original_key = settings.openai_api_key
    settings.intel_openai_fallback_enabled = True
    settings.openai_api_key = "sk-mock"
    try:
        client = EmbeddingClient(
            ollama_url=f"http://127.0.0.1:{mock_ollama_down}",
            openai_api_key="sk-mock",
        )
        # Force OpenAI URL to our mock by monkey-patching the request URL:
        # the simplest portable trick is to set the embedding model and
        # observe that fallback runs without crashing.
        # We instead use httpx mocking via a small subclass.
        import httpx as _h

        original = _h.AsyncClient

        class _Routed(original):
            def __init__(self, *a, **kw):
                super().__init__(*a, **kw)

            async def post(self, url, *a, **kw):  # type: ignore[override]
                rerouted = url.replace(
                    "https://api.openai.com",
                    f"http://127.0.0.1:{mock_ollama_down}",
                )
                return await super().post(rerouted, *a, **kw)

        _h.AsyncClient = _Routed
        try:
            vec = await client.embed_one("hello")
            assert len(vec) == settings.intel_embed_dim
        finally:
            _h.AsyncClient = original
    finally:
        settings.intel_openai_fallback_enabled = original_fb
        settings.openai_api_key = original_key


@pytest.mark.anyio
async def test_both_unavailable_raises():
    settings.intel_openai_fallback_enabled = False
    client = EmbeddingClient(ollama_url="http://127.0.0.1:1", timeout_sec=0.5)
    with pytest.raises(EmbeddingUnavailableError):
        await client.embed(["x"])
