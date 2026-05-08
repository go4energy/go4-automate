"""Pydantic-Schemas für Tenant-Stammdaten."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantMasterDataBase(BaseModel):
    """Gemeinsame Felder. Alle optional — Tenant kann sukzessive ausfüllen."""

    legal_name: str | None = Field(None, max_length=200, description="Firmierung wie im Handelsregister")
    display_name: str | None = Field(None, max_length=200, description="Anzeigename / Wortmarke")
    legal_form: str | None = Field(None, max_length=50, description="GmbH, AG, UG, GbR, Einzelunternehmen, ...")

    street: str | None = Field(None, max_length=200)
    street_number: str | None = Field(None, max_length=20)
    postal_code: str | None = Field(None, max_length=20)
    city: str | None = Field(None, max_length=100)
    country: str = Field("DE", max_length=2, description="ISO-3166-1 alpha-2")

    phone: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=300)

    managing_directors: list[str] | None = None
    register_court: str | None = Field(None, max_length=100, description="z.B. Würzburg")
    register_number: str | None = Field(None, max_length=50, description="z.B. HRB 12345")
    responsible_for_content: str | None = Field(
        None, max_length=200, description="V.i.S.d.P. nach §55 RStV"
    )

    vat_id: str | None = Field(None, max_length=30, description="USt-ID, z.B. DE123456789")
    tax_id: str | None = Field(None, max_length=30, description="Steuernummer (optional)")

    privacy_url: str | None = Field(None, max_length=300)
    imprint_url: str | None = Field(None, max_length=300)
    test_recipient_email: EmailStr | None = None
    default_disclaimer_html: str | None = None

    impressum_html_override: str | None = None

    unsubscribe_url_base: str | None = Field(
        None,
        max_length=300,
        description=(
            "Optionale Custom-URL-Base für Unsubscribe (z.B. "
            "'https://smartladen.de/abmelden/'). Tracking-Hash wird "
            "hinten angehängt. Leer = Default automate.go4.energy"
        ),
    )


class TenantMasterDataUpdate(TenantMasterDataBase):
    """Partial update — alle Felder optional."""


class TenantMasterDataResponse(TenantMasterDataBase):
    id: int
    tenant_id: str

    model_config = ConfigDict(from_attributes=True)


class ImpressumPreviewResponse(BaseModel):
    """Generated/effective impressum block for preview."""

    impressum_html: str
    is_override: bool
    is_complete: bool
    missing_fields: list[str]
