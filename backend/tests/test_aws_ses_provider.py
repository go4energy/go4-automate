"""Unit tests for the AWS SES email provider.

We mock boto3.client so the tests don't hit AWS. Focus is on:
- credential parsing from JSON-encrypted blob
- raw MIME message construction (Message-ID, multipart, headers)
- SES error handling
- credential verification
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.emailmarketing.encryption import encrypt_api_key
from app.emailmarketing.providers.aws_ses import (
    DEFAULT_REGION,
    AwsSesProvider,
    _parse_credentials,
)
from app.emailmarketing.providers.base import EmailMessage


def _ses_config(
    *,
    access_key: str = "AKIATEST",
    secret_key: str = "secret-key",
    region: str | None = None,
    configuration_set: str | None = None,
    sender_email: str = "info@smartladen.de",
    sender_name: str = "Smartladen",
    reply_to: str | None = None,
):
    payload: dict[str, str] = {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    if region:
        payload["region"] = region
    if configuration_set:
        payload["configuration_set"] = configuration_set
    encrypted = encrypt_api_key(json.dumps(payload))
    return SimpleNamespace(
        api_key_encrypted=encrypted,
        sender_email=sender_email,
        sender_name=sender_name,
        reply_to_email=reply_to,
    )


# ============== _parse_credentials ==============


def test_parse_credentials_full():
    cfg = _ses_config(
        region="eu-west-1",
        configuration_set="ses-bounces",
    )
    creds = _parse_credentials(cfg.api_key_encrypted)
    assert creds["aws_access_key_id"] == "AKIATEST"
    assert creds["aws_secret_access_key"] == "secret-key"
    assert creds["region"] == "eu-west-1"
    assert creds["configuration_set"] == "ses-bounces"


def test_parse_credentials_missing_raises():
    with pytest.raises(ValueError, match="missing"):
        _parse_credentials("")


def test_parse_credentials_invalid_json_raises():
    encrypted = encrypt_api_key("not-json")
    with pytest.raises(ValueError, match="Invalid"):
        _parse_credentials(encrypted)


def test_parse_credentials_partial_raises():
    encrypted = encrypt_api_key(json.dumps({"aws_access_key_id": "x"}))
    with pytest.raises(ValueError, match="must include"):
        _parse_credentials(encrypted)


# ============== Provider construction ==============


def test_provider_uses_default_region_when_unset():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)
    assert provider._region == DEFAULT_REGION
    assert provider._configuration_set is None


def test_provider_overrides_region_and_configuration_set():
    cfg = _ses_config(region="us-east-1", configuration_set="ses-bounces")
    provider = AwsSesProvider(cfg)
    assert provider._region == "us-east-1"
    assert provider._configuration_set == "ses-bounces"


# ============== Raw message construction ==============


def test_raw_message_includes_custom_message_id():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)
    msg = EmailMessage(
        to_email="lead@example.com",
        to_name="Lead",
        subject="Hallo",
        html_content="<p>Body</p>",
        text_content="Body",
        headers={"Message-ID": "<rcpt-42-abc12345@smartladen.de>"},
    )
    raw = provider._build_raw_message(msg).decode()
    assert "Message-ID: <rcpt-42-abc12345@smartladen.de>" in raw
    assert "Subject: Hallo" in raw
    assert "From: Smartladen <info@smartladen.de>" in raw
    assert "To: Lead <lead@example.com>" in raw


def test_raw_message_with_reply_to():
    cfg = _ses_config(reply_to="reply@smartladen.de")
    provider = AwsSesProvider(cfg)
    msg = EmailMessage(
        to_email="lead@example.com",
        to_name=None,
        subject="x",
        html_content="<p>x</p>",
    )
    raw = provider._build_raw_message(msg).decode()
    assert "Reply-To: reply@smartladen.de" in raw


def test_raw_message_explicit_headers_dont_clobber_subject():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)
    msg = EmailMessage(
        to_email="x@example.com",
        to_name=None,
        subject="Real Subject",
        html_content="<p>x</p>",
        headers={"Subject": "Override Attempt", "X-Custom": "value"},
    )
    raw = provider._build_raw_message(msg).decode()
    # Real subject wins; the duplicate from headers is not added
    assert raw.count("Subject:") == 1
    assert "Subject: Real Subject" in raw
    assert "X-Custom: value" in raw


def test_raw_message_html_only():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)
    msg = EmailMessage(
        to_email="x@example.com",
        to_name=None,
        subject="x",
        html_content="<p>HTML only</p>",
    )
    raw = provider._build_raw_message(msg).decode()
    assert "Content-Type: text/html" in raw


def test_raw_message_multipart_when_both_text_and_html():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)
    msg = EmailMessage(
        to_email="x@example.com",
        to_name=None,
        subject="x",
        html_content="<p>html</p>",
        text_content="text",
    )
    raw = provider._build_raw_message(msg).decode()
    assert "multipart/alternative" in raw
    assert "text" in raw
    assert "<p>html</p>" in raw


# ============== send_email — mocked boto3 ==============


@pytest.mark.asyncio
async def test_send_email_success():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)

    fake_client = MagicMock()
    fake_client.send_raw_email.return_value = {"MessageId": "ses-id-1"}

    with patch.object(provider, "_build_client", return_value=fake_client):
        msg = EmailMessage(
            to_email="lead@example.com",
            to_name=None,
            subject="x",
            html_content="<p>x</p>",
            headers={"Message-ID": "<rcpt-1-abc@smartladen.de>"},
        )
        result = await provider.send_email(msg)

    assert result.success is True
    assert result.message_id == "ses-id-1"
    fake_client.send_raw_email.assert_called_once()
    call = fake_client.send_raw_email.call_args
    assert call.kwargs["Source"] == "info@smartladen.de"
    assert call.kwargs["Destinations"] == ["lead@example.com"]


@pytest.mark.asyncio
async def test_send_email_with_configuration_set_passes_it():
    cfg = _ses_config(configuration_set="ses-bounces-smartladen")
    provider = AwsSesProvider(cfg)

    fake_client = MagicMock()
    fake_client.send_raw_email.return_value = {"MessageId": "id"}

    with patch.object(provider, "_build_client", return_value=fake_client):
        msg = EmailMessage(
            to_email="x@example.com",
            to_name=None,
            subject="x",
            html_content="<p>x</p>",
        )
        await provider.send_email(msg)

    call = fake_client.send_raw_email.call_args
    assert call.kwargs["ConfigurationSetName"] == "ses-bounces-smartladen"


@pytest.mark.asyncio
async def test_send_email_client_error():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)

    fake_client = MagicMock()
    fake_client.send_raw_email.side_effect = ClientError(
        {"Error": {"Code": "MessageRejected", "Message": "Email address not verified"}},
        "SendRawEmail",
    )

    with patch.object(provider, "_build_client", return_value=fake_client):
        msg = EmailMessage(
            to_email="unverified@example.com",
            to_name=None,
            subject="x",
            html_content="<p>x</p>",
        )
        result = await provider.send_email(msg)

    assert result.success is False
    assert "MessageRejected" in result.error
    assert "not verified" in result.error


# ============== verify_credentials ==============


@pytest.mark.asyncio
async def test_verify_credentials_success():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)

    fake_client = MagicMock()
    fake_client.get_send_quota.return_value = {"Max24HourSend": 200.0}

    with patch.object(provider, "_build_client", return_value=fake_client):
        ok = await provider.verify_credentials()

    assert ok is True


@pytest.mark.asyncio
async def test_verify_credentials_failure():
    cfg = _ses_config()
    provider = AwsSesProvider(cfg)

    fake_client = MagicMock()
    fake_client.get_send_quota.side_effect = ClientError(
        {"Error": {"Code": "InvalidClientTokenId", "Message": "bad creds"}},
        "GetSendQuota",
    )

    with patch.object(provider, "_build_client", return_value=fake_client):
        ok = await provider.verify_credentials()

    assert ok is False


# ============== Factory registration ==============


def test_factory_returns_aws_ses_provider():
    from app.emailmarketing.providers.base import get_provider

    cfg = _ses_config()
    cfg.provider_type = "aws_ses"
    provider = get_provider(cfg)
    assert isinstance(provider, AwsSesProvider)
