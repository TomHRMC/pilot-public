"""phase_5_2_fix_exclusion_constraints_and_add_indexes

Revision ID: 3c89a793b5e4
Revises: d2f994dbd6b6
Create Date: 2026-04-11 16:06:30.190594+00:00

Description:
Fixes 2 flawed exclusion constraints and adds 3 critical performance indexes
to align physical database with Golden Master JSON schema.

Reference:
- Analysis: dev-docs/analysis/phase-5.2-db-schema-sync-8-analysis.md
- Plan: dev-docs/analysis/phase-5.2-db-schema-sync-8-plan.md
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c89a793b5e4"
down_revision: str | None = "d2f994dbd6b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # =====================================================
    # PHASE 1: FIX EXCLUSION CONSTRAINTS
    # =====================================================

    # 1. Fix supplier_item_price.sip_no_overlap (add COALESCE logic)
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT sip_no_overlap;
    """)

    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT sip_no_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
            valid_period WITH &&
        );
    """)

    # 2. Fix pricebook_item_version.piv_no_overlap (add tenant_id parameter)
    op.execute("""
        ALTER TABLE pricebook_item_version
        DROP CONSTRAINT piv_no_overlap;
    """)

    op.execute("""
        ALTER TABLE pricebook_item_version
        ADD CONSTRAINT piv_no_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            pricebook_item_id WITH =,
            valid_period WITH &&
        );
    """)

    # =====================================================
    # PHASE 2: CREATE PERFORMANCE INDEXES
    # =====================================================
    # Note: CONCURRENTLY flag removed for development/test environment
    # For production deployment, use CONCURRENTLY with autocommit mode

    # 3. Create webhook_delivery_attempt worker queue index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_webhook_delivery_pending
        ON webhook_delivery_attempt (status, next_attempt_after);
    """)

    # 4. Create webhook_event tenant dashboard query index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_webhook_event_tenant_time
        ON webhook_event (tenant_id, created_at DESC);
    """)

    # 5. Create webhook_event entity lookup query index
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_webhook_event_entity
        ON webhook_event (entity_type_code, entity_id, created_at DESC);
    """)


def downgrade() -> None:
    # Drop indexes first
    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_event_entity;
    """)

    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_event_tenant_time;
    """)

    op.execute("""
        DROP INDEX IF EXISTS idx_webhook_delivery_pending;
    """)

    # Revert exclusion constraints to original (flawed) definitions

    # Revert pricebook_item_version
    op.execute("""
        ALTER TABLE pricebook_item_version
        DROP CONSTRAINT piv_no_overlap;
    """)

    op.execute("""
        ALTER TABLE pricebook_item_version
        ADD CONSTRAINT piv_no_overlap
        EXCLUDE USING gist (
            pricebook_item_id WITH =,
            valid_period WITH &&
        );
    """)

    # Revert supplier_item_price
    op.execute("""
        ALTER TABLE supplier_item_price
        DROP CONSTRAINT sip_no_overlap;
    """)

    op.execute("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT sip_no_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            tenant_id WITH =,
            valid_period WITH &&
        );
    """)
