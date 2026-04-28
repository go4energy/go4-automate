"""Tests for the Letterxpress v3 client.

Uses httpx.MockTransport to stub HTTP responses so no real API calls
are made.
"""

from __future__ import annotations

import base64
import hashlib
import json
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.letter import letterxpress_client as lxp_module
from app.letter.letterxpress_client import (
    LetterxpressClient,
    LetterxpressError,
)


def _stub_transport(handler):
    """Wrap a handler in MockTransport for use as `httpx.AsyncClient(transport=...)`."""
    return httpx.MockTransport(handler)


def _patch_async_client(monkeypatch, handler):
    """Make `httpx.AsyncClient(...)` always use the MockTransport."""
    transport = _stub_transport(handler)
    real_init = httpx.AsyncClient.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", fake_init)


@pytest.fixture
def client() -> LetterxpressClient:
    return LetterxpressClient(username="user", apikey="key", mode="test")


@pytest.mark.asyncio
async def test_get_balance(monkeypatch, client):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "status": 200,
                "message": "OK",
                "data": {"balance": 54.89, "currency": "EUR"},
            },
        )

    _patch_async_client(monkeypatch, handler)
    result = await client.get_balance()

    assert result.balance == Decimal("54.89")
    assert result.currency == "EUR"
    assert captured["url"].endswith("/v3/balance")
    assert captured["body"]["auth"] == {
        "username": "user",
        "apikey": "key",
        "mode": "test",
    }


@pytest.mark.asyncio
async def test_get_price(monkeypatch, client):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"status": 200, "message": "OK", "data": {"price": 4.99}},
        )

    _patch_async_client(monkeypatch, handler)
    price = await client.get_price(pages=2, color="4", c4=1)

    assert price == Decimal("4.99")
    spec = captured["body"]["letter"]["specification"]
    assert spec == {
        "pages": 2,
        "color": "4",
        "mode": "simplex",
        "shipping": "national",
        "c4": 1,
    }


@pytest.mark.asyncio
async def test_submit_letter_minimal(monkeypatch, client):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "status": 200,
                "message": "OK",
                "data": {
                    "id": 6035143,
                    "status": "queue",
                    "shipping": "national",
                    "mode": "simplex",
                    "color": "1",
                    "items": [
                        {
                            "address": "Max Mustermann, Musterstr. 1, 12345 Stadt",
                            "pages": 1,
                            "amount": 0.68,
                            "vat": 0.13,
                            "status": "queue",
                        }
                    ],
                },
            },
        )

    _patch_async_client(monkeypatch, handler)
    pdf = b"%PDF-1.4\n%fake\n"
    result = await client.submit_letter(pdf, filename_original="test.pdf")

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/v3/printjobs")

    letter = captured["body"]["letter"]
    expected_b64 = base64.b64encode(pdf).decode("utf-8")
    assert letter["base64_file"] == expected_b64
    assert (
        letter["base64_file_checksum"]
        == hashlib.md5(expected_b64.encode("utf-8")).hexdigest()
    )
    assert letter["specification"] == {
        "color": "1",
        "mode": "simplex",
        "shipping": "national",
        "c4": 1,
    }
    assert letter["filename_original"] == "test.pdf"

    assert result.job_id == 6035143
    assert result.status == "queue"
    assert result.pages == 1
    assert result.amount_net == Decimal("0.68")
    assert result.vat == Decimal("0.13")
    assert result.address_line.startswith("Max Mustermann")


@pytest.mark.asyncio
async def test_submit_letter_with_color_and_dispatch(monkeypatch, client):
    from datetime import date

    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "status": 200,
                "message": "OK",
                "data": {
                    "id": 1,
                    "status": "queue",
                    "items": [
                        {
                            "address": "X",
                            "pages": 2,
                            "amount": 1.5,
                            "vat": 0.3,
                            "status": "queue",
                        }
                    ],
                },
            },
        )

    _patch_async_client(monkeypatch, handler)
    await client.submit_letter(
        b"%PDF-",
        color="4",
        print_mode="duplex",
        c4=0,
        dispatch_date=date(2026, 5, 1),
        notice="ref-K7FQ2X",
    )

    letter = captured["body"]["letter"]
    assert letter["specification"]["color"] == "4"
    assert letter["specification"]["mode"] == "duplex"
    assert letter["specification"]["c4"] == 0
    assert letter["dispatch_date"] == "2026-05-01"
    assert letter["notice"] == "ref-K7FQ2X"


@pytest.mark.asyncio
async def test_submit_rejects_oversize_pdf(client):
    huge = b"x" * (lxp_module.MAX_PDF_SIZE_BYTES + 1)
    with pytest.raises(ValueError, match="zu groß"):
        await client.submit_letter(huge)


@pytest.mark.asyncio
async def test_submit_rejects_empty_pdf(client):
    with pytest.raises(ValueError, match="leer"):
        await client.submit_letter(b"")


@pytest.mark.asyncio
async def test_get_job(monkeypatch, client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/v3/printjobs/12345")
        return httpx.Response(
            200,
            json={
                "status": 200,
                "message": "OK",
                "data": {
                    "id": 12345,
                    "status": "done",
                    "shipping": "national",
                    "mode": "simplex",
                    "color": "1",
                    "created_at": "2026-04-28 10:00:00",
                    "updated_at": "2026-04-28 10:30:00",
                    "items": [
                        {
                            "address": "X",
                            "pages": 1,
                            "amount": 0.7,
                            "vat": 0.13,
                            "status": "sent",
                        }
                    ],
                },
            },
        )

    _patch_async_client(monkeypatch, handler)
    info = await client.get_job(12345)
    assert info.job_id == 12345
    assert info.status == "done"
    assert info.amount_net == Decimal("0.7")


@pytest.mark.asyncio
async def test_unauthorized_raises(monkeypatch, client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "Unauthorized."})

    _patch_async_client(monkeypatch, handler)
    with pytest.raises(LetterxpressError) as exc:
        await client.get_balance()
    assert "Unauthorized" in str(exc.value)


@pytest.mark.asyncio
async def test_http_error_raises(monkeypatch, client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    _patch_async_client(monkeypatch, handler)
    with pytest.raises(LetterxpressError, match="HTTP-Fehler"):
        await client.get_balance()


@pytest.mark.asyncio
async def test_invalid_credentials_raises_at_init():
    with pytest.raises(ValueError):
        LetterxpressClient(username="", apikey="x")
    with pytest.raises(ValueError):
        LetterxpressClient(username="x", apikey="x", mode="bogus")  # type: ignore


@pytest.mark.asyncio
async def test_delete_job(monkeypatch, client):
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(
            200, json={"status": 200, "message": "Print job deleted successfully"}
        )

    _patch_async_client(monkeypatch, handler)
    await client.delete_job(99)
    assert captured["method"] == "DELETE"
    assert captured["url"].endswith("/v3/printjobs/99")
