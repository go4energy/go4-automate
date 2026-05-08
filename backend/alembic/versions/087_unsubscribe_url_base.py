"""Add unsubscribe_url_base to tenant_master_data.

Erlaubt pro Tenant eine eigene Unsubscribe-URL-Base, z.B.
``https://smartladen.de/abmelden/`` — der Renderer hängt den Tracking-Hash
hinten an. Wenn leer, wird ``settings.app_url + /api/v1/emailmarketing/t/u/``
als Fallback genutzt (default ``https://automate.go4.energy/...``).

Use-Case: Empfänger sieht in Cold-Mail-Footer den smartladen.de-Domain-
Namen statt automate.go4.energy — bessere Brand-Konsistenz und
Vertrauen. Setzt voraus dass smartladen.de selbst einen Reverse-Proxy
oder eigene Confirmation-Page bereitstellt.

Revision ID: 087
Revises: 086
Create Date: 2026-05-08
"""

import sqlalchemy as sa

from alembic import op

revision: str = "087"
down_revision: str | None = "086"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_master_data",
        sa.Column("unsubscribe_url_base", sa.String(300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_master_data", "unsubscribe_url_base")
