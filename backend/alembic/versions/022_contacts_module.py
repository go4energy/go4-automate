"""Contacts module - Contact and Company tables.

Revision ID: 022
Revises: 021
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create companies table first (contacts reference it)
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Basic Info
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(200), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        # Details
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("annual_revenue", sa.String(50), nullable=True),
        # Address (JSONB)
        sa.Column("address", JSONB, nullable=True),
        # Contact Info
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        # Metadata
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        # Timestamps
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
            onupdate=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_companies_tenant_name", "companies", ["tenant_id", "name"]
    )
    op.create_index(
        "ix_companies_tenant_domain", "companies", ["tenant_id", "domain"]
    )

    # Create contacts table
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.String(50),
            sa.ForeignKey("tenants.tenant_id"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Basic Info
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("mobile", sa.String(50), nullable=True),
        sa.Column("position", sa.String(100), nullable=True),
        # Avatar
        sa.Column("avatar_url", sa.String(500), nullable=True),
        # Metadata
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("custom_fields", JSONB, nullable=False, server_default="{}"),
        # Social
        sa.Column("linkedin", sa.String(200), nullable=True),
        sa.Column("twitter", sa.String(200), nullable=True),
        # Notes
        sa.Column("notes", sa.Text(), nullable=True),
        # Timestamps
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
            onupdate=sa.func.now(),
        ),
    )

    op.create_unique_constraint(
        "uq_contacts_tenant_email", "contacts", ["tenant_id", "email"]
    )
    op.create_index(
        "ix_contacts_tenant_email", "contacts", ["tenant_id", "email"]
    )
    op.create_index(
        "ix_contacts_tenant_name", "contacts", ["tenant_id", "name"]
    )
    op.create_index(
        "ix_contacts_tenant_company", "contacts", ["tenant_id", "company_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_contacts_tenant_company", "contacts")
    op.drop_index("ix_contacts_tenant_name", "contacts")
    op.drop_index("ix_contacts_tenant_email", "contacts")
    op.drop_constraint("uq_contacts_tenant_email", "contacts")
    op.drop_table("contacts")

    op.drop_index("ix_companies_tenant_domain", "companies")
    op.drop_index("ix_companies_tenant_name", "companies")
    op.drop_table("companies")
