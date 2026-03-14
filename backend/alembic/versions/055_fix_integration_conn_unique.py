"""Fix integration_connections unique constraint to use mailbox_address.

Revision ID: 055
Revises: 054
Create Date: 2026-03-14
"""

from alembic import op

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_integration_conn_tenant_user_provider_type_email",
        "integration_connections",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_integration_conn_tenant_user_provider_type_mailbox",
        "integration_connections",
        ["tenant_id", "user_id", "provider", "integration_type", "mailbox_address"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_integration_conn_tenant_user_provider_type_mailbox",
        "integration_connections",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_integration_conn_tenant_user_provider_type_email",
        "integration_connections",
        ["tenant_id", "user_id", "provider", "integration_type", "connected_email"],
    )
