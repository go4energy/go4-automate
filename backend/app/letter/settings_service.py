"""Letter module settings (Letterxpress credentials, defaults).

Stores and retrieves tenant-scoped configuration in the existing
``module_parameters`` table — no new schema, no new tables.
Sensitive values (the API key) are encrypted at rest using the same
Fernet helper that the email module uses, so an EMAIL_ENCRYPTION_KEY
already protects them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.emailmarketing.encryption import (
    decrypt_api_key,
    encrypt_api_key,
    is_encrypted,
)
from app.exceptions import AppError
from app.letter.letterxpress_client import LetterxpressClient

LETTER_MODULE = "letter"

# Definition der Letter-Module-Parameter. Wird beim Tenant-Onboarding
# in module_parameters geseedet und vom Frontend Settings-Tab gelesen.
LETTER_PARAMS: list[dict[str, Any]] = [
    {
        "variable": "letterxpress_username",
        "description": "Letterxpress LXP-API Benutzername (aus dem Letterxpress-Kundenbereich)",
        "var_type": "string",
        "required": True,
        "sort_order": 10,
        "default": "",
    },
    {
        "variable": "letterxpress_apikey",
        "description": "Letterxpress LXP-API Key (verschlüsselt gespeichert)",
        "var_type": "password",
        "required": True,
        "sort_order": 20,
        "default": "",
    },
    {
        "variable": "letterxpress_default_mode",
        "description": "Standard-Versandmodus (test = Postbox / live = direkt versenden)",
        "var_type": "string",
        "required": True,
        "sort_order": 30,
        "default": "test",
    },
    {
        "variable": "letterxpress_default_color",
        "description": "Standard-Farbdruck (1 = Schwarz/Weiß, 4 = Vollfarbe CMYK)",
        "var_type": "string",
        "required": False,
        "sort_order": 40,
        "default": "4",
    },
    {
        "variable": "letterxpress_c4_envelope",
        "description": "C4-Kuvert verwenden (1 = ja, ab 9+ Seiten meist Pflicht)",
        "var_type": "string",
        "required": False,
        "sort_order": 50,
        "default": "1",
    },
    {
        "variable": "letterxpress_default_shipping",
        "description": "Standard-Versand (national / international / auto)",
        "var_type": "string",
        "required": False,
        "sort_order": 60,
        "default": "national",
    },
]


@dataclass
class LetterSettings:
    """Resolved settings for a tenant. Values come decrypted."""

    username: str
    apikey: str
    mode: str  # test | live
    color: str  # "1" | "4"
    c4: int  # 0 | 1
    shipping: str  # national | international | auto

    @property
    def is_complete(self) -> bool:
        return bool(self.username and self.apikey)


class LetterSettingsError(AppError):
    """Raised when Letter settings are missing or unusable."""

    def __init__(self, detail: str):
        super().__init__(message=f"Letter-Konfiguration: {detail}", status_code=400)


async def ensure_module_parameters(db: AsyncSession, tenant_id: str) -> None:
    """Seed the LETTER_PARAMS rows for a tenant if they don't exist yet.

    Idempotent — already-existing variables are left untouched (so a
    tenant's edited values are never overwritten).
    """
    existing = await db.execute(
        text(
            "SELECT variable FROM module_parameters "
            "WHERE tenant_id = :tid AND module = :mod"
        ),
        {"tid": tenant_id, "mod": LETTER_MODULE},
    )
    have = {row[0] for row in existing.fetchall()}
    for spec in LETTER_PARAMS:
        if spec["variable"] in have:
            continue
        await db.execute(
            text(
                "INSERT INTO module_parameters "
                "(tenant_id, module, variable, description, value, var_type, "
                " required, sort_order, created_at, updated_at) "
                "VALUES (:tid, :mod, :var, :desc, :val, :vt, :req, :so, "
                "        :now, :now)"
            ),
            {
                "tid": tenant_id,
                "mod": LETTER_MODULE,
                "var": spec["variable"],
                "desc": spec["description"],
                "val": spec["default"],
                "vt": spec["var_type"],
                "req": spec["required"],
                "so": spec["sort_order"],
                "now": datetime.utcnow(),
            },
        )
    await db.flush()


async def _read_param(db: AsyncSession, tenant_id: str, variable: str) -> str | None:
    r = await db.execute(
        text(
            "SELECT value FROM module_parameters "
            "WHERE tenant_id=:tid AND module=:mod AND variable=:var"
        ),
        {"tid": tenant_id, "mod": LETTER_MODULE, "var": variable},
    )
    row = r.first()
    return row[0] if row else None


async def get_letter_settings(
    db: AsyncSession,
    tenant_id: str,
) -> LetterSettings:
    """Read all Letter settings for a tenant. Decrypts the API key."""
    raw_apikey = await _read_param(db, tenant_id, "letterxpress_apikey") or ""
    apikey = decrypt_api_key(raw_apikey) if is_encrypted(raw_apikey) else raw_apikey

    mode = (await _read_param(db, tenant_id, "letterxpress_default_mode")) or "test"
    color = (await _read_param(db, tenant_id, "letterxpress_default_color")) or "4"
    c4_raw = (await _read_param(db, tenant_id, "letterxpress_c4_envelope")) or "1"
    shipping = (
        await _read_param(db, tenant_id, "letterxpress_default_shipping")
    ) or "national"

    return LetterSettings(
        username=(await _read_param(db, tenant_id, "letterxpress_username")) or "",
        apikey=apikey,
        mode=mode if mode in ("test", "live") else "test",
        color=color if color in ("1", "4") else "4",
        c4=1 if str(c4_raw).strip() in ("1", "true", "True") else 0,
        shipping=shipping
        if shipping in ("national", "international", "auto")
        else "national",
    )


async def set_letter_setting(
    db: AsyncSession,
    tenant_id: str,
    variable: str,
    value: str,
) -> None:
    """Persist a single setting. API key is encrypted before storage."""
    spec = next((p for p in LETTER_PARAMS if p["variable"] == variable), None)
    if spec is None:
        raise LetterSettingsError(f"unbekannte Variable {variable!r}")

    stored_value = encrypt_api_key(value) if spec["var_type"] == "password" else value

    # Upsert
    existing = await _read_param(db, tenant_id, variable)
    if existing is None:
        await db.execute(
            text(
                "INSERT INTO module_parameters "
                "(tenant_id, module, variable, description, value, var_type, "
                " required, sort_order, created_at, updated_at) "
                "VALUES (:tid, :mod, :var, :desc, :val, :vt, :req, :so, :now, :now)"
            ),
            {
                "tid": tenant_id,
                "mod": LETTER_MODULE,
                "var": variable,
                "desc": spec["description"],
                "val": stored_value,
                "vt": spec["var_type"],
                "req": spec["required"],
                "so": spec["sort_order"],
                "now": datetime.utcnow(),
            },
        )
    else:
        await db.execute(
            text(
                "UPDATE module_parameters SET value = :val, updated_at = :now "
                "WHERE tenant_id = :tid AND module = :mod AND variable = :var"
            ),
            {
                "tid": tenant_id,
                "mod": LETTER_MODULE,
                "var": variable,
                "val": stored_value,
                "now": datetime.utcnow(),
            },
        )
    await db.flush()


async def get_letterxpress_client(
    db: AsyncSession,
    tenant_id: str,
    *,
    override_mode: str | None = None,
) -> LetterxpressClient:
    """Build a LetterxpressClient from the tenant's stored settings.

    Raises LetterSettingsError if username or apikey are missing.
    Pass ``override_mode='test'|'live'`` to force a specific mode for a
    single send (e.g. when the user clicks "Senden Live").
    """
    settings = await get_letter_settings(db, tenant_id)
    if not settings.is_complete:
        raise LetterSettingsError(
            "Letterxpress-Zugangsdaten sind nicht hinterlegt. "
            "Bitte unter Letter → Einstellungen Username + API-Key setzen."
        )
    mode = override_mode or settings.mode
    if mode not in ("test", "live"):
        raise LetterSettingsError(f"ungültiger Mode {mode!r}")
    logger.debug(
        "Letterxpress client for tenant={t} mode={m}",
        t=tenant_id,
        m=mode,
    )
    return LetterxpressClient(
        username=settings.username,
        apikey=settings.apikey,
        mode=mode,
    )
