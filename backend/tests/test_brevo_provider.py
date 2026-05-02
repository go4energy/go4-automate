"""Unit tests for the Brevo email provider."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.emailmarketing.encryption import encrypt_api_key
from app.emailmarketing.providers.base import EmailMessage
from app.emailmarketing.providers.brevo import BREVO_API_URL, BrevoProvider


def _config(*, api_key: str = "xkeysib-test", reply_to: str | None = None):
    return SimpleNamespace(
        api_key_encrypted=encrypt_api_key(api_key),
        sender_email="info@smartladen.de",
        sender_name="Smartladen",
        reply_to_email=reply_to,
    )


def _msg(**overrides):
    base = {
        "to_email": "lead@example.com",
        "to_name": "Lead",
        "subject": "Hallo",
        "html_content": "<p>Body</p>",
    }
    base.update(overrides)
    return EmailMessage(**base)


def test_payload_basic_structure():
    provider = BrevoProvider(_config())
    payload = provider._build_payload(_msg())
    assert payload["sender"] == {"email": "info@smartladen.de", "name": "Smartladen"}
    assert payload["to"] == [{"email": "lead@example.com", "name": "Lead"}]
    assert payload["subject"] == "Hallo"
    assert payload["htmlContent"] == "<p>Body</p>"


def test_payload_includes_custom_message_id_header():
    provider = BrevoProvider(_config())
    payload = provider._build_payload(
        _msg(headers={"Message-ID": "<rcpt-42-abc12345@smartladen.de>"})
    )
    assert payload["headers"] == {"Message-ID": "<rcpt-42-abc12345@smartladen.de>"}


def test_payload_with_text_and_html():
    provider = BrevoProvider(_config())
    payload = provider._build_payload(
        _msg(html_content="<p>html</p>", text_content="text")
    )
    assert payload["htmlContent"] == "<p>html</p>"
    assert payload["textContent"] == "text"


def test_payload_with_reply_to_from_config():
    provider = BrevoProvider(_config(reply_to="reply@smartladen.de"))
    payload = provider._build_payload(_msg())
    assert payload["replyTo"] == {"email": "reply@smartladen.de"}


def test_payload_filters_none_headers():
    provider = BrevoProvider(_config())
    payload = provider._build_payload(
        _msg(headers={"Message-ID": "<x@x>", "X-Skip": None})
    )
    assert "X-Skip" not in payload["headers"]
    assert payload["headers"]["Message-ID"] == "<x@x>"


def test_payload_tracking_token_lands_in_params():
    provider = BrevoProvider(_config())
    payload = provider._build_payload(_msg(tracking_token="uuid-1234"))
    assert payload["params"] == {"tracking_token": "uuid-1234"}


@pytest.mark.asyncio
async def test_send_email_success():
    provider = BrevoProvider(_config())

    fake_response = MagicMock()
    fake_response.status_code = 201
    fake_response.content = b'{"messageId":"<brevo-id>"}'
    fake_response.json = lambda: {"messageId": "<brevo-id>"}

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch("app.emailmarketing.providers.brevo.httpx.AsyncClient", return_value=fake_client):
        result = await provider.send_email(_msg())

    assert result.success is True
    assert result.message_id == "<brevo-id>"
    fake_client.post.assert_awaited_once()
    args, kwargs = fake_client.post.call_args
    assert args[0] == f"{BREVO_API_URL}/smtp/email"
    assert kwargs["headers"]["api-key"] == "xkeysib-test"


@pytest.mark.asyncio
async def test_send_email_4xx_error():
    provider = BrevoProvider(_config())

    fake_response = MagicMock()
    fake_response.status_code = 400
    fake_response.text = '{"code":"invalid_parameter","message":"sender invalid"}'

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.post = AsyncMock(return_value=fake_response)

    with patch("app.emailmarketing.providers.brevo.httpx.AsyncClient", return_value=fake_client):
        result = await provider.send_email(_msg())

    assert result.success is False
    assert "400" in result.error


@pytest.mark.asyncio
async def test_send_email_timeout():
    provider = BrevoProvider(_config())

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.emailmarketing.providers.brevo.httpx.AsyncClient", return_value=fake_client):
        result = await provider.send_email(_msg())

    assert result.success is False
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_verify_credentials_ok():
    provider = BrevoProvider(_config())

    fake_response = MagicMock()
    fake_response.status_code = 200

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=fake_response)

    with patch("app.emailmarketing.providers.brevo.httpx.AsyncClient", return_value=fake_client):
        ok = await provider.verify_credentials()

    assert ok is True


@pytest.mark.asyncio
async def test_verify_credentials_unauthorized():
    provider = BrevoProvider(_config())

    fake_response = MagicMock()
    fake_response.status_code = 401

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=fake_response)

    with patch("app.emailmarketing.providers.brevo.httpx.AsyncClient", return_value=fake_client):
        ok = await provider.verify_credentials()

    assert ok is False


def test_factory_returns_brevo_provider():
    from app.emailmarketing.providers.base import get_provider

    cfg = _config()
    cfg.provider_type = "brevo"
    provider = get_provider(cfg)
    assert isinstance(provider, BrevoProvider)
