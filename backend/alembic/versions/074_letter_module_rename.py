"""Letter module rename: postmail → letter.

Renames postmail tables to their letter-namespaced equivalents and
rewrites the channel string ``postmail`` to ``letter`` inside the
``engagement_pipelines.channels`` JSONB array.

Tables:
  postmail_templates → letter_templates
  postmail_letters   → letters
  postmail_batches   → letter_batches

Foreign keys to the renamed tables update automatically because
PostgreSQL stores them by relation OID.

Revision ID: 074
Revises: 073
Create Date: 2026-04-28
"""

from alembic import op

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename tables
    op.rename_table("postmail_templates", "letter_templates")
    op.rename_table("postmail_letters", "letters")
    op.rename_table("postmail_batches", "letter_batches")

    # Rewrite channel string in engagement_pipelines.channels (JSONB array)
    op.execute(
        """
        UPDATE engagement_pipelines
        SET channels = (
            SELECT jsonb_agg(
                CASE WHEN value::text = '"postmail"' THEN '"letter"'::jsonb ELSE value END
            )
            FROM jsonb_array_elements(channels) AS value
        )
        WHERE channels::text LIKE '%"postmail"%'
        """
    )

    # Rewrite channel column in contact_activities (defensive — should be 0 rows)
    op.execute(
        "UPDATE contact_activities SET channel = 'letter' WHERE channel = 'postmail'"
    )

    # Rewrite module column in pending_actions (defensive — should be 0 rows)
    op.execute(
        "UPDATE pending_actions SET module = 'letter' WHERE module = 'postmail'"
    )

    # Rewrite module_key in tenant_module_licenses (defensive — should be 0 rows)
    op.execute(
        "UPDATE tenant_module_licenses SET module_key = 'letter' WHERE module_key = 'postmail'"
    )

    # Rewrite module column in module_parameters / module_contexts (defensive)
    op.execute(
        "UPDATE module_parameters SET module = 'letter' WHERE module = 'postmail'"
    )
    op.execute(
        "UPDATE module_contexts SET module = 'letter' WHERE module = 'postmail'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE module_contexts SET module = 'postmail' WHERE module = 'letter'"
    )
    op.execute(
        "UPDATE module_parameters SET module = 'postmail' WHERE module = 'letter'"
    )
    op.execute(
        "UPDATE tenant_module_licenses SET module_key = 'postmail' WHERE module_key = 'letter'"
    )
    op.execute(
        "UPDATE pending_actions SET module = 'postmail' WHERE module = 'letter'"
    )
    op.execute(
        "UPDATE contact_activities SET channel = 'postmail' WHERE channel = 'letter'"
    )

    op.execute(
        """
        UPDATE engagement_pipelines
        SET channels = (
            SELECT jsonb_agg(
                CASE WHEN value::text = '"letter"' THEN '"postmail"'::jsonb ELSE value END
            )
            FROM jsonb_array_elements(channels) AS value
        )
        WHERE channels::text LIKE '%"letter"%'
        """
    )

    op.rename_table("letter_batches", "postmail_batches")
    op.rename_table("letters", "postmail_letters")
    op.rename_table("letter_templates", "postmail_templates")
