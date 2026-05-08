"""Fix integration_connections unique constraint to use mailbox_address.

For existing databases created with the old 054, this migration swaps the
constraint from connected_email to mailbox_address.
For fresh installs where 054 already uses mailbox_address, this is a no-op.

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
    conn = op.get_bind()
    # Check if old constraint exists (from pre-fix 054)
    from sqlalchemy import inspect

    inspector = inspect(conn)
    constraints = inspector.get_unique_constraints("integration_connections")
    old_exists = any(
        c["name"] == "uq_integration_conn_tenant_user_provider_type_email"
        for c in constraints
    )

    if old_exists:
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
