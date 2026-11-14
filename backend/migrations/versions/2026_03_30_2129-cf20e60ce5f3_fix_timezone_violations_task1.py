"""fix_timezone_violations_task1

Revision ID: cf20e60ce5f3
Revises: cbf672175f02
Create Date: 2026-03-30 21:29:12.653799+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf20e60ce5f3"
down_revision: str | None = "cbf672175f02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Phase 4.5 Task 1: Fix timezone violations (9 columns)
    # Use USING clause to safely convert existing timestamp data to timestamptz
    # All existing timestamps are assumed to be in UTC

    op.execute("""
        ALTER TABLE idempotency_key
          ALTER COLUMN first_seen_at
          TYPE timestamp with time zone
          USING first_seen_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE integration_sync_mapping
          ALTER COLUMN last_synced_at
          TYPE timestamp with time zone
          USING last_synced_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE notification_event
          ALTER COLUMN occurred_at
          TYPE timestamp with time zone
          USING occurred_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE pricebook_item_version
          ALTER COLUMN recorded_at
          TYPE timestamp with time zone
          USING recorded_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE product_plan_product_feature_version
          ALTER COLUMN recorded_at
          TYPE timestamp with time zone
          USING recorded_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE product_plan_version
          ALTER COLUMN recorded_at
          TYPE timestamp with time zone
          USING recorded_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE quote_public_link_contact_action
          ALTER COLUMN occurred_at
          TYPE timestamp with time zone
          USING occurred_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE tax_rate_version
          ALTER COLUMN recorded_at
          TYPE timestamp with time zone
          USING recorded_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE tenant_markup_version
          ALTER COLUMN recorded_at
          TYPE timestamp with time zone
          USING recorded_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    # Downgrade: Revert timezone-aware columns back to timestamp without time zone
    # Note: This removes timezone information but preserves the UTC timestamp values

    op.execute("""
        ALTER TABLE tenant_markup_version
          ALTER COLUMN recorded_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE tax_rate_version
          ALTER COLUMN recorded_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE quote_public_link_contact_action
          ALTER COLUMN occurred_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE product_plan_version
          ALTER COLUMN recorded_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE product_plan_product_feature_version
          ALTER COLUMN recorded_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE pricebook_item_version
          ALTER COLUMN recorded_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE notification_event
          ALTER COLUMN occurred_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE integration_sync_mapping
          ALTER COLUMN last_synced_at
          TYPE timestamp without time zone
    """)

    op.execute("""
        ALTER TABLE idempotency_key
          ALTER COLUMN first_seen_at
          TYPE timestamp without time zone
    """)
