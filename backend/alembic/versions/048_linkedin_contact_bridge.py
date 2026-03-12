"""Add contact_id FK to linkedin_contacts for central contact linking.

Revision ID: 048_linkedin_contact_bridge
Revises: 047_postmail_module
Create Date: 2026-03-08

"""

from alembic import op
import sqlalchemy as sa

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linkedin_contacts",
        sa.Column(
            "central_contact_id",
            sa.Integer(),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_linkedin_contacts_central_contact",
        "linkedin_contacts",
        ["tenant_id", "central_contact_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_linkedin_contacts_central_contact", "linkedin_contacts")
    op.drop_column("linkedin_contacts", "central_contact_id")
