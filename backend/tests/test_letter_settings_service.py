"""Tests for the Letter settings service.

Verifies the module_parameters seeding, encryption round-trip, and
client factory.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.letter.settings_service import (
    LETTER_PARAMS,
    LetterSettingsError,
    ensure_module_parameters,
    get_letter_settings,
    get_letterxpress_client,
    set_letter_setting,
)

TENANT = "test-tenant"


@pytest.mark.asyncio
async def test_ensure_module_parameters_seeds_defaults(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    await db_session.flush()

    settings = await get_letter_settings(db_session, TENANT)
    assert settings.username == ""
    assert settings.apikey == ""
    assert settings.mode == "test"
    assert settings.color == "4"
    assert settings.c4 == 1
    assert settings.shipping == "national"
    assert settings.is_complete is False


@pytest.mark.asyncio
async def test_ensure_is_idempotent(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    await ensure_module_parameters(db_session, TENANT)  # again
    # Pre-set a value, then seed again — must not overwrite
    await set_letter_setting(db_session, TENANT, "letterxpress_username", "edited")
    await ensure_module_parameters(db_session, TENANT)

    settings = await get_letter_settings(db_session, TENANT)
    assert settings.username == "edited"


@pytest.mark.asyncio
async def test_set_and_read_username(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    await set_letter_setting(db_session, TENANT, "letterxpress_username", "lxp_user")
    settings = await get_letter_settings(db_session, TENANT)
    assert settings.username == "lxp_user"


@pytest.mark.asyncio
async def test_apikey_round_trip(db_session: AsyncSession):
    """API key must be retrievable as plaintext, even though stored encrypted."""
    await ensure_module_parameters(db_session, TENANT)
    raw_key = "test-secret-apikey-1234567890"
    await set_letter_setting(db_session, TENANT, "letterxpress_apikey", raw_key)

    settings = await get_letter_settings(db_session, TENANT)
    assert settings.apikey == raw_key


@pytest.mark.asyncio
async def test_set_letter_setting_rejects_unknown_variable(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    with pytest.raises(LetterSettingsError, match="unbekannte Variable"):
        await set_letter_setting(db_session, TENANT, "totally_made_up", "x")


@pytest.mark.asyncio
async def test_get_client_complains_when_credentials_missing(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    with pytest.raises(LetterSettingsError, match="Zugangsdaten"):
        await get_letterxpress_client(db_session, TENANT)


@pytest.mark.asyncio
async def test_get_client_builds_with_credentials(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    await set_letter_setting(db_session, TENANT, "letterxpress_username", "user")
    await set_letter_setting(db_session, TENANT, "letterxpress_apikey", "key")

    client = await get_letterxpress_client(db_session, TENANT)
    assert client.mode == "test"

    client_live = await get_letterxpress_client(
        db_session, TENANT, override_mode="live"
    )
    assert client_live.mode == "live"


@pytest.mark.asyncio
async def test_get_client_rejects_invalid_override(db_session: AsyncSession):
    await ensure_module_parameters(db_session, TENANT)
    await set_letter_setting(db_session, TENANT, "letterxpress_username", "u")
    await set_letter_setting(db_session, TENANT, "letterxpress_apikey", "k")
    with pytest.raises(LetterSettingsError, match="ungültiger Mode"):
        await get_letterxpress_client(db_session, TENANT, override_mode="bogus")


@pytest.mark.asyncio
async def test_settings_falls_back_to_defaults_for_invalid_values(
    db_session: AsyncSession,
):
    await ensure_module_parameters(db_session, TENANT)
    await set_letter_setting(db_session, TENANT, "letterxpress_default_mode", "weird")
    await set_letter_setting(db_session, TENANT, "letterxpress_default_color", "9")

    settings = await get_letter_settings(db_session, TENANT)
    assert settings.mode == "test"  # invalid → default
    assert settings.color == "4"  # invalid → default


def test_letter_params_definition_is_complete():
    variables = {p["variable"] for p in LETTER_PARAMS}
    assert "letterxpress_username" in variables
    assert "letterxpress_apikey" in variables
    assert "letterxpress_default_mode" in variables
    # Apikey must be a password type for encryption to kick in
    apikey_spec = next(p for p in LETTER_PARAMS if p["variable"] == "letterxpress_apikey")
    assert apikey_spec["var_type"] == "password"
    assert apikey_spec["required"] is True
