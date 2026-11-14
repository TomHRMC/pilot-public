"""phase_fe_1_batch_b18_tenant_user_skill_employee_columns

FIND-066 (S2 High) — B18 schema-only: Add 2 nullable columns to tenant_user table.

Columns added:
  - skill_level_code VARCHAR NULL — technician skill tier per-tenant
    (apprentice/journeyman/master/foreman). No CHECK constraint — values are
    tenant-configurable in Phase 2. Cross-dependency: FIND-056 labor rate
    lookup reads this column; code wiring done in B20 via FIND-056.
  - employee_number VARCHAR NULL — optional HR/payroll reference ID; useful for
    Phase 2 payroll export and roster integrations.

No code changes in B18 — columns are schema scaffolding for B20.

Revision ID: bb2c8fd5f1de
Revises: 6c6276144ee0
Create Date: 2026-05-12 16:42:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bb2c8fd5f1de"
down_revision = "6c6276144ee0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_user",
        sa.Column("skill_level_code", sa.String(), nullable=True),
    )
    op.add_column(
        "tenant_user",
        sa.Column("employee_number", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenant_user", "employee_number")
    op.drop_column("tenant_user", "skill_level_code")
