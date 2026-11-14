"""phase_fe_1_batch_b7b_mobile_sync_event_resolution_action

Revision ID: f6220c8d00ae
Revises: 04953bca8e66
Create Date: 2026-05-01 21:53:29

B7b / A45 — Tech-Resolvable Conflict UI Endpoints
Adds resolution_action column to mobile_sync_event and seeds the
mobile_sync.resolve permission to technician and owner roles.

Design doc §F.6: mobile_sync.resolve is a NEW permission — not pre-existing.
Granted to technician and owner roles. Allows tech to resolve own conflicts.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f6220c8d00ae"
down_revision = "04953bca8e66"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add resolution_action column to mobile_sync_event                 #
    # ------------------------------------------------------------------ #
    op.add_column(
        "mobile_sync_event",
        sa.Column("resolution_action", sa.Text(), nullable=True),
    )
    op.execute("""
        ALTER TABLE public.mobile_sync_event
        ADD CONSTRAINT chk_mobile_sync_event_resolution_action
        CHECK (resolution_action IS NULL OR
               resolution_action IN ('use_local', 'use_server', 'escalate_to_owner'));
    """)

    # ------------------------------------------------------------------ #
    # 2. Seed mobile_sync.resolve permission (F.6)                         #
    # ------------------------------------------------------------------ #
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["mobile_sync.resolve"]'::jsonb,
            updated_at  = NOW()
        WHERE code IN ('technician', 'owner')
          AND NOT (permissions @> '["mobile_sync.resolve"]'::jsonb);
    """)

    # mobile_sync.view is also needed for the GET endpoint (tech views own conflicts)
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["mobile_sync.view"]'::jsonb,
            updated_at  = NOW()
        WHERE code IN ('technician', 'owner')
          AND NOT (permissions @> '["mobile_sync.view"]'::jsonb);
    """)


def downgrade() -> None:
    # Reverse RBAC seed
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN ('"mobile_sync.resolve"', '"mobile_sync.view"')
        ),
        updated_at = NOW()
        WHERE code IN ('technician', 'owner');
    """)

    # Remove check constraint and column
    op.execute(
        "ALTER TABLE public.mobile_sync_event DROP CONSTRAINT IF EXISTS chk_mobile_sync_event_resolution_action;"
    )
    op.drop_column("mobile_sync_event", "resolution_action")
