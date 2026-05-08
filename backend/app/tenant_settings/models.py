"""Tenant-Stammdaten ORM-Modelle.

Eine Zeile pro Tenant. Pflichtangaben gemäß §5 TMG (Impressum) und
§55 RStV (Verantwortlicher) plus Compliance-Hilfen für Cold-Mail-Footer.
"""

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class TenantMasterData(TimestampMixin, Base):
    """Pflichtangaben + Compliance-Daten pro Tenant."""

    __tablename__ = "tenant_master_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Firma
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    legal_form: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Adresse
    street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    street_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="DE")

    # Kontakt
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Vertretung & Register
    managing_directors: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    register_court: Mapped[str | None] = mapped_column(String(100), nullable=True)
    register_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    responsible_for_content: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

    # Steuer
    vat_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Compliance
    privacy_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    imprint_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    test_recipient_email: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    default_disclaimer_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Override für Sonderfälle (Vereine, Stiftungen, Kanzleien)
    impressum_html_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Custom Unsubscribe-URL-Base (z.B. https://smartladen.de/abmelden/)
    # Wenn gesetzt, wird der Tracking-Hash hinten angehängt. Der Webserver
    # auf der Custom-Domain muss dann den Pfad implementieren (Reverse-Proxy
    # oder eigene Page). Wenn leer, fallback auf settings.app_url.
    unsubscribe_url_base: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )

    tenant = relationship("Tenant")

    __table_args__ = (
        Index("ix_tenant_master_data_tenant", "tenant_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<TenantMasterData {self.tenant_id} legal_name={self.legal_name!r}>"
