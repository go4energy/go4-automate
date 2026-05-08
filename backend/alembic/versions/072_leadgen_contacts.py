"""Leadgen: dedicated contacts table + LinkedIn fields on places.

Splits the previously-string-only ``managing_directors`` list and the
``primary_contact`` JSON-blob into individual rows so each person can carry
their own LinkedIn URL, gender, role and provenance. The new table is the
source of truth for the Apollo CSV export and for the ``linkedin`` worker
stage; legacy columns on ``leadgen_impressum`` / ``leadgen_llm_insights``
are kept untouched for backward compatibility.

Revision ID: 072
Revises: 071
Create Date: 2026-04-27
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Place-level LinkedIn (one company URL per place) ---
    op.add_column(
        "leadgen_places",
        sa.Column("linkedin_company_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "leadgen_places",
        sa.Column(
            "linkedin_company_match_method",
            sa.String(30),
            nullable=True,
        ),
    )

    # --- Companies: platform-wide LinkedIn URL ---
    # Mirrors ``contacts.linkedin`` (already exists, 200 chars). Populated
    # during leadgen handoff and queryable in CRM views.
    op.add_column(
        "companies",
        sa.Column("linkedin_url", sa.String(500), nullable=True),
    )

    # --- New table: leadgen_contacts (one row per person) ---
    op.create_table(
        "leadgen_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(50), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        # Identity
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        # LinkedIn
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        # impressum_link | serper | manual | null
        sa.Column("linkedin_match_method", sa.String(30), nullable=True),
        sa.Column("linkedin_match_confidence", sa.Float(), nullable=True),
        # Gender for salutation
        # "male" | "female" | None
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("gender_confidence", sa.Float(), nullable=True),
        # library | llm | manual | jsonb_legacy
        sa.Column("gender_method", sa.String(20), nullable=True),
        # Provenance
        # managing_director | primary_contact | impressum_link | manual
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column(
            "is_handed_off",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("contact_id", sa.Integer(), nullable=True),
        # Free-form bag for future fields (LLM gender notes, raw_serper_hit, ...)
        sa.Column(
            "extra",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
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
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.tenant_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["place_id"], ["leadgen_places.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"], ["contacts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        # Same person should only appear once per place; the backfill relies
        # on this for idempotency.
        sa.UniqueConstraint(
            "place_id", "full_name", name="uq_leadgen_contacts_place_name"
        ),
    )
    op.create_index(
        "ix_leadgen_contacts_tenant_place",
        "leadgen_contacts",
        ["tenant_id", "place_id"],
    )
    op.create_index(
        "ix_leadgen_contacts_tenant_handoff",
        "leadgen_contacts",
        ["tenant_id", "is_handed_off"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_leadgen_contacts_tenant_handoff", table_name="leadgen_contacts"
    )
    op.drop_index(
        "ix_leadgen_contacts_tenant_place", table_name="leadgen_contacts"
    )
    op.drop_table("leadgen_contacts")
    op.drop_column("companies", "linkedin_url")
    op.drop_column("leadgen_places", "linkedin_company_match_method")
    op.drop_column("leadgen_places", "linkedin_company_url")
