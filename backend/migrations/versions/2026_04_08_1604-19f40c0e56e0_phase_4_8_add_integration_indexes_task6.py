"""phase_4_8_add_integration_indexes_task6

Revision ID: 19f40c0e56e0
Revises: c813644a6395
Create Date: 2026-04-08 16:04:50.419316+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19f40c0e56e0"
down_revision: str | None = "c813644a6395"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composite indexes for integration domain tables.

    These indexes optimize QuickBooks sync operations:
    - idx_ism_entity: Entity type + ID lookups (AevoFab → QuickBooks)
    - idx_ism_external: External system + ID lookups (QuickBooks → AevoFab)
    - idx_isc_tenant_status: Tenant-scoped conflict filtering
    - idx_isl_tenant_service: Tenant-scoped sync history queries
    """
    # Sync mapping indexes for bidirectional entity lookups
    op.create_index(
        "idx_ism_entity", "integration_sync_mapping", ["entity_type_code", "entity_id"]
    )

    op.create_index(
        "idx_ism_external",
        "integration_sync_mapping",
        ["app_service_id", "external_id"],
    )

    # Sync conflict index for tenant-scoped filtering
    op.create_index(
        "idx_isc_tenant_status", "integration_sync_conflict", ["tenant_id", "status"]
    )

    # Sync log index with time ordering for history queries
    op.create_index(
        "idx_isl_tenant_service",
        "integration_sync_log",
        ["tenant_id", "app_service_id", sa.text("started_at DESC")],
    )


def downgrade() -> None:
    """Remove integration domain composite indexes."""
    op.drop_index("idx_isl_tenant_service", table_name="integration_sync_log")
    op.drop_index("idx_isc_tenant_status", table_name="integration_sync_conflict")
    op.drop_index("idx_ism_external", table_name="integration_sync_mapping")
    op.drop_index("idx_ism_entity", table_name="integration_sync_mapping")
