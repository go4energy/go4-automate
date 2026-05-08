"""Tenant-Stammdaten Service — get/update + Impressum-Generator."""

from html import escape

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tenant_settings.models import TenantMasterData
from app.tenant_settings.schemas import TenantMasterDataUpdate

# Pflichtfelder für ein vollständiges §5 TMG-Impressum.
# Zusätzliche Pflicht je nach Branche (z.B. Berufshaftpflicht für Anwälte/Ärzte) — out of scope.
_REQUIRED_FIELDS = (
    "legal_name",
    "street",
    "postal_code",
    "city",
    "phone",
    "email",
    "managing_directors",
    "register_court",
    "register_number",
    "vat_id",
)


class TenantMasterDataService:
    """CRUD + Impressum-Generierung."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, tenant_id: str) -> TenantMasterData | None:
        """Lookup. Returns None if no row yet (Tenant hat nie gepflegt)."""
        return (
            await self.db.execute(
                select(TenantMasterData).where(
                    TenantMasterData.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()

    async def upsert(
        self, tenant_id: str, data: TenantMasterDataUpdate
    ) -> TenantMasterData:
        """Insert or update — eine Zeile pro Tenant. Idempotent."""
        row = await self.get(tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if row is None:
            row = TenantMasterData(tenant_id=tenant_id, **update_data)
            self.db.add(row)
        else:
            for key, value in update_data.items():
                setattr(row, key, value)

        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def missing_fields(self, tenant_id: str) -> list[str]:
        """Liste der ungesetzten Pflichtfelder. Leere Liste = vollständig."""
        row = await self.get(tenant_id)
        if row is None:
            return list(_REQUIRED_FIELDS)
        missing = []
        for field in _REQUIRED_FIELDS:
            value = getattr(row, field, None)
            if not value:
                missing.append(field)
        return missing


def build_impressum_block(data: TenantMasterData | None) -> str:
    """Baut den §5 TMG-konformen Impressum-HTML-Block aus den Stammdaten.

    Wenn ``impressum_html_override`` gesetzt ist, wird dieser zurückgegeben
    (für Sonderfälle wie Vereine, Stiftungen, Kanzleien mit zusätzlichen
    Pflichtangaben).

    Bei fehlenden Daten: leerer String — Renderer fällt darauf nicht zurück
    auf Default-Text, weil ein unvollständiges Impressum schlimmer wäre als
    keines (schließt §5 TMG nicht erfüllbar — explizite Lücke statt Falsch-
    info).
    """
    if data is None:
        return ""

    if data.impressum_html_override:
        return data.impressum_html_override

    # Fehlt das Wesentliche → kein Block
    if not (data.legal_name and data.street and data.postal_code and data.city):
        return ""

    parts: list[str] = []
    parts.append('<div style="font-size:11px;line-height:1.5;color:#666;">')

    # Firma + Rechtsform
    legal = escape(data.legal_name or "")
    if data.legal_form:
        legal = f"{legal}"  # bei „Smartladen.de GmbH" steckt Rechtsform schon im Namen
    parts.append(f"<strong>{legal}</strong><br>")

    # Adresse
    street_full = escape(data.street or "")
    if data.street_number:
        street_full = f"{street_full} {escape(data.street_number)}"
    parts.append(f"{street_full}<br>")
    parts.append(
        f"{escape(data.postal_code or '')} {escape(data.city or '')}, "
        f"{escape(data.country or 'DE')}<br>"
    )

    # Kontakt
    if data.phone:
        parts.append(f"Tel.: {escape(data.phone)}<br>")
    if data.email:
        parts.append(
            f'E-Mail: <a href="mailto:{escape(data.email)}" style="color:#666;">{escape(data.email)}</a><br>'
        )
    if data.website:
        url = data.website if data.website.startswith("http") else f"https://{data.website}"
        parts.append(
            f'Web: <a href="{escape(url)}" style="color:#666;">{escape(data.website)}</a><br>'
        )

    # Vertretung
    if data.managing_directors:
        directors = ", ".join(escape(d) for d in data.managing_directors if d)
        if directors:
            parts.append(f"<br>Vertretungsberechtigt: {directors}<br>")
    if data.responsible_for_content and data.responsible_for_content not in (
        ", ".join(data.managing_directors or [])
    ):
        parts.append(
            f"Verantwortlich i.S.d. § 55 Abs. 2 RStV: {escape(data.responsible_for_content)}<br>"
        )

    # Register
    if data.register_court and data.register_number:
        parts.append(
            f"Registergericht: {escape(data.register_court)} · "
            f"Registernummer: {escape(data.register_number)}<br>"
        )

    # Steuer
    if data.vat_id:
        parts.append(f"USt-IdNr.: {escape(data.vat_id)}<br>")
    if data.tax_id:
        parts.append(f"Steuernummer: {escape(data.tax_id)}<br>")

    parts.append("</div>")
    return "".join(parts)


def build_disclaimer_block(data: TenantMasterData | None) -> str:
    """DSGVO/UWG-Disclaimer für Cold-Mail-Footer.

    Wenn ``default_disclaimer_html`` gesetzt → eigene Formulierung.
    Sonst Standard-Block der berechtigtes Interesse + Werbewiderspruch
    transparent macht.
    """
    if data and data.default_disclaimer_html:
        return data.default_disclaimer_html

    privacy_link = ""
    if data and data.privacy_url:
        privacy_link = (
            f' Datenschutzhinweise: <a href="{escape(data.privacy_url)}" '
            f'style="color:#888;">{escape(data.privacy_url)}</a>.'
        )

    contact_email = (data.email if data else None) or ""
    werbewid = (
        f' Werbewiderspruch jederzeit formlos per Antwort an '
        f'{escape(contact_email)}.'
        if contact_email
        else ""
    )

    return (
        '<p style="font-size:11px;line-height:1.5;color:#888;margin:0 0 12px;">'
        "Sie erhalten diese E-Mail einmalig auf Basis berechtigten Interesses "
        "(§ 7 Abs. 3 UWG / Art. 6 Abs. 1 lit. f DSGVO), weil Ihr Betrieb für "
        "uns als Geschäftspartner in Frage kommt."
        f"{werbewid}{privacy_link}"
        "</p>"
    )
