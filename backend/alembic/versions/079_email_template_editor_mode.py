"""Add editor_mode column to email_templates.

Three editor modes per template — chosen at creation, switchable later
with a UI warning that content may be lost when changing types:

- ``unlayer`` (default) — Drag-&-Drop visual editor (Unlayer/iframe).
  ``design_json`` is the source of truth, ``html_content`` is the export.
- ``plain`` — Plain-text only mail (no HTML, just a text block).
  ``text_content`` is the source of truth.
- ``html`` — Raw HTML editor (CodeMirror) with optional KI-chat assistant
  for generation/modification. ``html_content`` is the source of truth,
  ``design_json`` is null.

Revision ID: 079
Revises: 078
Create Date: 2026-05-02
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "079"
down_revision: str | None = "078"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "email_templates",
        sa.Column(
            "editor_mode",
            sa.String(length=20),
            nullable=False,
            server_default="unlayer",
        ),
    )
    # Backfill: existing templates with design_json keep 'unlayer';
    # those without get 'html' (raw HTML was the original mode).
    op.execute(
        """
        UPDATE email_templates
        SET editor_mode = CASE
            WHEN design_json IS NOT NULL THEN 'unlayer'
            ELSE 'html'
        END
        """
    )


def downgrade() -> None:
    op.drop_column("email_templates", "editor_mode")
