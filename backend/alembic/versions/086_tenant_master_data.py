"""Tenant-Stammdaten-Tabelle für rechtskonforme Email-Footer.

Eine Zeile pro Tenant mit allen Pflichtangaben gemäß §5 TMG (Impressum)
und §55 RStV (Verantwortlicher) plus Compliance-Hilfen für DSGVO-Footer
in Cold-Mails. Der ``email_marketing.render_service`` zieht daraus
``{{impressum_block}}``, ``{{disclaimer_block}}`` und die Tracking-URLs.

Felder zerfallen in sechs logische Gruppen:
- Firma
- Adresse
- Kontakt
- Vertretung & Handelsregister
- Steuer
- Compliance (Datenschutz, Disclaimer, Test-Empfänger)

Plus ``impressum_html_override`` als Sonderfall: Wenn gesetzt, wird der
generierte Block durch diesen Roh-HTML ersetzt — z.B. für Tenants mit
ungewöhnlichen Rechtskonstrukten (Vereine, Stiftungen, Kanzleien).

Revision ID: 086
Revises: 085
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "086"
down_revision: str | None = "085"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "tenant_master_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Firma
        sa.Column("legal_name", sa.String(200), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("legal_form", sa.String(50), nullable=True),
        # Adresse
        sa.Column("street", sa.String(200), nullable=True),
        sa.Column("street_number", sa.String(20), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(2), nullable=False, server_default="DE"),
        # Kontakt
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("website", sa.String(300), nullable=True),
        # Vertretung & Register
        # JSONB-Liste z.B. ["Harry Ketschik", "Max Mustermann"]
        sa.Column("managing_directors", JSONB(), nullable=True),
        sa.Column("register_court", sa.String(100), nullable=True),
        sa.Column("register_number", sa.String(50), nullable=True),
        sa.Column("responsible_for_content", sa.String(200), nullable=True),
        # Steuer
        sa.Column("vat_id", sa.String(30), nullable=True),
        sa.Column("tax_id", sa.String(30), nullable=True),
        # Compliance
        sa.Column("privacy_url", sa.String(300), nullable=True),
        sa.Column("imprint_url", sa.String(300), nullable=True),
        sa.Column("test_recipient_email", sa.String(200), nullable=True),
        sa.Column("default_disclaimer_html", sa.Text(), nullable=True),
        # Override für Sonderfälle
        sa.Column("impressum_html_override", sa.Text(), nullable=True),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_tenant_master_data_tenant",
        "tenant_master_data",
        ["tenant_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_master_data_tenant", table_name="tenant_master_data")
    op.drop_table("tenant_master_data")
