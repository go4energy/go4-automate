"""Migrate data from briefing_account_connections to integration_connections.

Copies existing briefing connections into the new general-purpose table
so that both the briefing and assistant modules share one connection store.

Revision ID: 056
Revises: 055
Create Date: 2026-03-14
"""

import json

import sqlalchemy as sa

from alembic import op

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if source table exists (it may not in fresh installs)
    inspector = sa.inspect(conn)
    if "briefing_account_connections" not in inspector.get_table_names():
        return

    # Read all existing briefing connections
    briefing_conns = conn.execute(
        sa.text(
            "SELECT id, tenant_id, user_id, provider, integration_type, "
            "connected_email, encrypted_token, scopes, status, "
            "last_synced_at, last_error, created_at, updated_at "
            "FROM briefing_account_connections"
        )
    ).fetchall()

    if not briefing_conns:
        return

    for row in briefing_conns:
        scopes = row.scopes
        if isinstance(scopes, str):
            try:
                scopes = json.loads(scopes)
            except json.JSONDecodeError:
                # Preserve unexpected legacy values without double-encoding them.
                scopes = row.scopes

        # Map briefing provider names to integration provider names
        provider = row.provider
        if provider == "microsoft":
            provider = "microsoft_graph"
        elif provider == "google":
            provider = "google_workspace"

        # Check if already migrated (avoid duplicates)
        existing = conn.execute(
            sa.text(
                "SELECT id FROM integration_connections "
                "WHERE tenant_id = :tid AND user_id = :uid "
                "AND provider = :prov AND integration_type = :itype "
                "AND mailbox_address = :mailbox"
            ),
            {
                "tid": row.tenant_id,
                "uid": row.user_id,
                "prov": provider,
                "itype": row.integration_type,
                "mailbox": row.connected_email,
            },
        ).fetchone()

        if existing:
            continue

        # Insert into integration_connections
        conn.execute(
            sa.text(
                "INSERT INTO integration_connections "
                "(tenant_id, user_id, provider, integration_type, auth_mode, "
                "connected_email, mailbox_address, account_label, "
                "encrypted_token, scopes, status, "
                "last_synced_at, last_error, metadata_json, created_at, updated_at) "
                "VALUES (:tid, :uid, :prov, :itype, 'delegated', "
                ":email, :mailbox, :label, "
                ":token, :scopes, :status, "
                ":synced, :error, :meta, :created, :updated)"
            ),
            {
                "tid": row.tenant_id,
                "uid": row.user_id,
                "prov": provider,
                "itype": row.integration_type,
                "email": row.connected_email,
                "mailbox": row.connected_email,
                "label": row.connected_email,
                "token": row.encrypted_token,
                "scopes": json.dumps(scopes) if scopes is not None else None,
                "status": row.status or "pending",
                "synced": row.last_synced_at,
                "error": row.last_error,
                "meta": '{"migrated_from": "briefing_account_connections"}',
                "created": row.created_at,
                "updated": row.updated_at,
            },
        )


def downgrade() -> None:
    # Remove migrated rows (identifiable by metadata)
    op.execute(
        sa.text(
            "DELETE FROM integration_connections "
            "WHERE metadata_json->>'migrated_from' = 'briefing_account_connections'"
        )
    )
