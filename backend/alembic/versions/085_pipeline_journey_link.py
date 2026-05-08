"""Engagement-Pipeline ↔ Customer-Journey Verknüpfung.

Verheiratet die Engagement-Pipelines mit der existierenden Customer-Journey-
Infrastruktur, damit Tracking-Links pro (Empfänger, Kampagne) saubere
``ref_code``-Werte tragen statt des permanenten Cookie-Hashs:

- ``engagement_pipelines.journey_campaign_id`` → optionale Verknüpfung zur
  ``journey_campaigns``. Wird beim ersten Render einer Mail per
  ``CampaignService.ensure_for_pipeline`` per Name-Match angelegt/wieder­
  gefunden (idempotent).
- ``pipeline_enrollments.journey_ref_code_id`` → Cache-Pointer auf den
  ``journey_ref_codes``-Datensatz, der für (Contact, Campaign) angelegt
  wurde. Erspart den Renderer einen zweiten Lookup pro Mail.
- ``UNIQUE (contact_id, campaign_id)`` auf ``journey_ref_codes`` schützt
  vor Race-Conditions wenn mehrere Worker parallel rendern und denselben
  Code zu erzeugen versuchen. Vor dem Anlegen werden bestehende Doubletten
  bereinigt (älteste Zeile bleibt, jüngere fliegen raus).

Revision ID: 085
Revises: 084
Create Date: 2026-05-04
"""

import sqlalchemy as sa

from alembic import op

revision: str = "085"
down_revision: str | None = "084"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. Pipeline ↔ Journey-Campaign-FK
    op.add_column(
        "engagement_pipelines",
        sa.Column(
            "journey_campaign_id",
            sa.Integer(),
            sa.ForeignKey("journey_campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_engagement_pipelines_journey_campaign",
        "engagement_pipelines",
        ["journey_campaign_id"],
    )

    # 2. Enrollment ↔ Ref-Code-FK (Cache-Pointer)
    op.add_column(
        "pipeline_enrollments",
        sa.Column(
            "journey_ref_code_id",
            sa.Integer(),
            sa.ForeignKey("journey_ref_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_pipeline_enrollments_journey_ref_code",
        "pipeline_enrollments",
        ["journey_ref_code_id"],
    )

    # 3. Doubletten in journey_ref_codes bereinigen, dann UNIQUE-Constraint
    #    Behalte älteste Zeile pro (contact_id, campaign_id), Rest weg.
    op.execute(
        """
        DELETE FROM journey_ref_codes
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY contact_id, campaign_id
                           ORDER BY id ASC
                       ) AS rn
                FROM journey_ref_codes
                WHERE contact_id IS NOT NULL
                  AND campaign_id IS NOT NULL
            ) t
            WHERE t.rn > 1
        )
        """
    )

    # Partial-UNIQUE — schließt NULL-Kombinationen aus (legitime ungeknüpfte
    # Codes wie "kein Contact" oder "kein Campaign" bleiben erlaubt).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_journey_ref_per_contact_campaign
        ON journey_ref_codes (contact_id, campaign_id)
        WHERE contact_id IS NOT NULL AND campaign_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_journey_ref_per_contact_campaign")
    op.drop_index(
        "ix_pipeline_enrollments_journey_ref_code",
        table_name="pipeline_enrollments",
    )
    op.drop_column("pipeline_enrollments", "journey_ref_code_id")
    op.drop_index(
        "ix_engagement_pipelines_journey_campaign",
        table_name="engagement_pipelines",
    )
    op.drop_column("engagement_pipelines", "journey_campaign_id")
